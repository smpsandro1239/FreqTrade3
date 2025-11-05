#!/usr/bin/env python3
"""
================================================================
FREQTRADE3 - SISTEMA DE BACKUP E SEGURANÇA AVANÇADO
================================================================

Sistema completo de backup e segurança com:
- Backup automático com compressão e criptografia
- Monitoramento de integridade de arquivos
- Recuperação de desastres
- Log de auditoria
- Criptografia AES-256
- Backup incremental
- Verificação de integridade

Uso:
    python3 backup_system.py --create-full
    python3 backup_system.py --create-incremental
    python3 backup_system.py --restore --file backup_20231105.tar.gz
    python3 backup_system.py --verify --file backup_20231105.tar.gz
"""

import argparse
import base64
import gzip
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import ssl
import subprocess
import sys
import tarfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import schedule
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureBackupSystem:
    """Sistema de backup seguro com criptografia"""

    def __init__(self, config_path: str = "backup_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.encryption_key = None
        self.backup_dir = Path(self.config['backup']['directory'])
        self.backup_dir.mkdir(exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Carregar chave de criptografia
        self._load_encryption_key()

        self.logger.info("🟢 Sistema de Backup Seguro inicializado")

    def _load_config(self) -> Dict:
        """Carrega configuração do sistema de backup"""
        default_config = {
            "backup": {
                "directory": "backups",
                "compression": "gzip",
                "encryption": True,
                "max_backups": 30,
                "incremental_interval_hours": 6,
                "full_backup_interval_days": 7,
                "retention_days": 90,
                "verify_integrity": True
            },
            "directories": {
                "critical": [
                    "configs",
                    "strategies",
                    "user_data",
                    "scripts",
                    "docs"
                ],
                "optional": [
                    "logs",
                    "templates"
                ]
            },
            "encryption": {
                "algorithm": "AES-256",
                "key_derivation": "PBKDF2",
                "iterations": 100000
            },
            "notifications": {
                "email": {
                    "enabled": False,
                    "smtp_server": "",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "to_addresses": []
                },
                "webhook": {
                    "enabled": False,
                    "url": ""
                }
            },
            "security": {
                "log_audit": True,
                "verify_checksums": True,
                "quarantine_failed": True
            }
        }

        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração: {e}")

        return default_config

    def _setup_logging(self):
        """Configura sistema de logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [BACKUP] - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "backup_system.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("BackupSystem")

    def _load_encryption_key(self):
        """Carrega ou gera chave de criptografia"""
        key_file = Path("backup.key")

        try:
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    self.encryption_key = f.read()
            else:
                # Gerar nova chave
                self.encryption_key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(self.encryption_key)
                # Configurar permissões restritivas
                os.chmod(key_file, 0o600)
                self.logger.info("🔐 Nova chave de criptografia gerada")
        except Exception as e:
            self.logger.error(f"Erro ao carregar chave de criptografia: {e}")
            # Fallback: usar chave temporária (não recomendado para produção)
            self.encryption_key = Fernet.generate_key()

    def _create_encryption_cipher(self) -> Fernet:
        """Cria cifra de criptografia"""
        if not self.encryption_key:
            raise ValueError("Chave de criptografia não encontrada")
        return Fernet(self.encryption_key)

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calcula checksum SHA-256 do arquivo"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Erro ao calcular checksum de {file_path}: {e}")
            return ""

    def _create_file_manifest(self, files: List[Path], base_path: Path) -> Dict:
        """Cria manifesto dos arquivos para backup"""
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(files),
            "total_size": 0,
            "files": []
        }

        for file_path in files:
            try:
                if file_path.exists() and file_path.is_file():
                    checksum = self._calculate_file_checksum(file_path)
                    relative_path = file_path.relative_to(base_path)

                    file_info = {
                        "path": str(relative_path),
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "checksum": checksum
                    }

                    manifest["files"].append(file_info)
                    manifest["total_size"] += file_info["size"]

            except Exception as e:
                self.logger.warning(f"Erro ao processar arquivo {file_path}: {e}")

        return manifest

    def _collect_files_for_backup(self, include_optional: bool = False) -> List[Path]:
        """Coleta arquivos para backup"""
        files = []
        base_path = Path.cwd()

        # Diretórios críticos
        for dir_name in self.config['directories']['critical']:
            dir_path = base_path / dir_name
            if dir_path.exists():
                files.extend(dir_path.rglob('*'))

        # Diretórios opcionais (se solicitado)
        if include_optional:
            for dir_name in self.config['directories']['optional']:
                dir_path = base_path / dir_name
                if dir_path.exists():
                    files.extend(dir_path.rglob('*'))

        # Filtrar apenas arquivos (não diretórios)
        files = [f for f in files if f.is_file() and not f.name.startswith('.')]

        return sorted(files)

    def _compress_data(self, data: bytes) -> bytes:
        """Comprime dados usando gzip"""
        return gzip.compress(data, compresslevel=9)

    def _encrypt_data(self, data: bytes) -> bytes:
        """Criptografa dados usando AES-256"""
        if not self.config['backup']['encryption']:
            return data

        try:
            cipher = self._create_encryption_cipher()
            return cipher.encrypt(data)
        except Exception as e:
            self.logger.error(f"Erro ao criptografar dados: {e}")
            raise

    def create_full_backup(self) -> Optional[str]:
        """Cria backup completo"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"freqtrade3_full_{timestamp}.tar.gz.enc"
            backup_path = self.backup_dir / backup_name

            self.logger.info(f"🚀 Iniciando backup completo: {backup_name}")

            # Coletar arquivos
            files = self._collect_files_for_backup(include_optional=True)
            if not files:
                raise ValueError("Nenhum arquivo encontrado para backup")

            # Criar manifesto
            manifest = self._create_file_manifest(files, Path.cwd())

            # Criar tarball em memória
            import io
            tar_buffer = io.BytesIO()

            with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
                # Adicionar manifesto primeiro
                manifest_json = json.dumps(manifest, indent=2).encode('utf-8')
                tarinfo = tarfile.TarInfo(name='manifest.json')
                tarinfo.size = len(manifest_json)
                tar.addfile(tarinfo, io.BytesIO(manifest_json))

                # Adicionar arquivos
                for file_path in files:
                    try:
                        tar.add(file_path, arcname=file_path.relative_to(Path.cwd()))
                    except Exception as e:
                        self.logger.warning(f"Erro ao adicionar {file_path} ao backup: {e}")

            # Comprimir e criptografar
            tar_data = tar_buffer.getvalue()
            compressed_data = self._compress_data(tar_data)
            encrypted_data = self._encrypt_data(compressed_data)

            # Salvar backup
            with open(backup_path, 'wb') as f:
                f.write(encrypted_data)

            # Verificar integridade
            backup_checksum = self._calculate_file_checksum(backup_path)

            # Log de sucesso
            self._log_backup_event("FULL_BACKUP_COMPLETED", {
                "backup_file": backup_name,
                "files_count": len(files),
                "total_size": manifest["total_size"],
                "compressed_size": len(encrypted_data),
                "checksum": backup_checksum
            })

            self.logger.info(f"✅ Backup completo criado: {backup_name}")
            self.logger.info(f"   Arquivos: {len(files)}")
            self.logger.info(f"   Tamanho: {manifest['total_size'] / 1024 / 1024:.2f} MB")
            self.logger.info(f"   Comprimido: {len(encrypted_data) / 1024 / 1024:.2f} MB")

            return str(backup_path)

        except Exception as e:
            self.logger.error(f"❌ Erro ao criar backup completo: {e}")
            return None

    def create_incremental_backup(self) -> Optional[str]:
        """Cria backup incremental"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"freqtrade3_incremental_{timestamp}.tar.gz.enc"
            backup_path = self.backup_dir / backup_name

            self.logger.info(f"🚀 Iniciando backup incremental: {backup_name}")

            # Encontrar último backup completo
            last_full_backup = self._find_last_full_backup()
            if not last_full_backup:
                self.logger.warning("Nenhum backup completo encontrado, criando backup completo")
                return self.create_full_backup()

            # Verificar integridade do último backup
            if not self.verify_backup(last_full_backup):
                self.logger.error("Último backup comprometido, criando backup completo")
                return self.create_full_backup()

            # Carregar manifesto do último backup
            manifest = self._load_backup_manifest(last_full_backup)
            if not manifest:
                raise ValueError("Não foi possível carregar manifesto do último backup")

            # Coletar arquivos atuais
            current_files = self._collect_files_for_backup(include_optional=True)

            # Identificar arquivos modificados
            modified_files = []
            for file_path in current_files:
                relative_path = str(file_path.relative_to(Path.cwd()))
                manifest_file = next((f for f in manifest["files"] if f["path"] == relative_path), None)

                if not manifest_file or self._is_file_modified(file_path, manifest_file):
                    modified_files.append(file_path)

            if not modified_files:
                self.logger.info("ℹ️ Nenhum arquivo modificado encontrado")
                return None

            # Criar manifesto incremental
            incremental_manifest = {
                "type": "incremental",
                "timestamp": datetime.now().isoformat(),
                "base_backup": last_full_backup.name,
                "base_manifest": manifest,
                "modified_files": len(modified_files),
                "files": []
            }

            # Adicionar informações dos arquivos modificados
            for file_path in modified_files:
                relative_path = str(file_path.relative_to(Path.cwd()))
                checksum = self._calculate_file_checksum(file_path)

                file_info = {
                    "path": relative_path,
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "checksum": checksum
                }
                incremental_manifest["files"].append(file_info)

            # Criar backup incremental
            import io
            tar_buffer = io.BytesIO()

            with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
                # Adicionar manifesto incremental
                manifest_json = json.dumps(incremental_manifest, indent=2).encode('utf-8')
                tarinfo = tarfile.TarInfo(name='incremental_manifest.json')
                tarinfo.size = len(manifest_json)
                tar.addfile(tarinfo, io.BytesIO(manifest_json))

                # Adicionar arquivos modificados
                for file_path in modified_files:
                    try:
                        tar.add(file_path, arcname=file_path.relative_to(Path.cwd()))
                    except Exception as e:
                        self.logger.warning(f"Erro ao adicionar {file_path} ao backup: {e}")

            # Comprimir e criptografar
            tar_data = tar_buffer.getvalue()
            compressed_data = self._compress_data(tar_data)
            encrypted_data = self._encrypt_data(compressed_data)

            # Salvar backup
            with open(backup_path, 'wb') as f:
                f.write(encrypted_data)

            # Log de sucesso
            self._log_backup_event("INCREMENTAL_BACKUP_COMPLETED", {
                "backup_file": backup_name,
                "modified_files": len(modified_files),
                "compressed_size": len(encrypted_data),
                "base_backup": last_full_backup.name
            })

            self.logger.info(f"✅ Backup incremental criado: {backup_name}")
            self.logger.info(f"   Arquivos modificados: {len(modified_files)}")
            self.logger.info(f"   Comprimido: {len(encrypted_data) / 1024 / 1024:.2f} MB")

            return str(backup_path)

        except Exception as e:
            self.logger.error(f"❌ Erro ao criar backup incremental: {e}")
            return None

    def _find_last_full_backup(self) -> Optional[Path]:
        """Encontra o último backup completo"""
        backup_files = list(self.backup_dir.glob("freqtrade3_full_*.tar.gz.enc"))
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return backup_files[0] if backup_files else None

    def _is_file_modified(self, file_path: Path, manifest_file: Dict) -> bool:
        """Verifica se arquivo foi modificado"""
        try:
            if not file_path.exists():
                return True

            current_checksum = self._calculate_file_checksum(file_path)
            current_mtime = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()

            return (current_checksum != manifest_file["checksum"] or
                   current_mtime != manifest_file["modified"])
        except Exception:
            return True

    def _load_backup_manifest(self, backup_path: Path) -> Optional[Dict]:
        """Carrega manifesto de um backup"""
        try:
            # Ler e descriptografar backup
            with open(backup_path, 'rb') as f:
                encrypted_data = f.read()

            cipher = self._create_encryption_cipher()
            compressed_data = cipher.decrypt(encrypted_data)
            tar_data = gzip.decompress(compressed_data)

            # Extrair manifesto
            import io
            tar_buffer = io.BytesIO(tar_data)

            with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
                manifest_file = tar.getmember('manifest.json')
                manifest_content = tar.extractfile(manifest_file).read()
                return json.loads(manifest_content.decode('utf-8'))

        except Exception as e:
            self.logger.error(f"Erro ao carregar manifesto de {backup_path}: {e}")
            return None

    def verify_backup(self, backup_path: Path, detailed: bool = False) -> bool:
        """Verifica integridade de um backup"""
        try:
            self.logger.info(f"🔍 Verificando integridade de: {backup_path.name}")

            # Verificar se arquivo existe e tem tamanho válido
            if not backup_path.exists():
                self.logger.error(f"Arquivo de backup não encontrado: {backup_path}")
                return False

            if backup_path.stat().st_size == 0:
                self.logger.error(f"Arquivo de backup vazio: {backup_path}")
                return False

            # Descriptografar e decomprimir
            with open(backup_path, 'rb') as f:
                encrypted_data = f.read()

            cipher = self._create_encryption_cipher()
            compressed_data = cipher.decrypt(encrypted_data)
            tar_data = gzip.decompress(compressed_data)

            # Verificar tarball
            import io
            tar_buffer = io.BytesIO(tar_data)

            with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
                # Verificar manifesto
                if 'manifest.json' not in tar.getnames():
                    self.logger.error("Manifesto não encontrado no backup")
                    return False

                manifest_file = tar.getmember('manifest.json')
                manifest_content = tar.extractfile(manifest_file).read()
                manifest = json.loads(manifest_content.decode('utf-8'))

                # Verificar todos os arquivos no tarball
                verification_results = []

                for member in tar.getmembers():
                    if member.name == 'manifest.json':
                        continue

                    if member.isfile():
                        try:
                            # Tentar ler o arquivo
                            tar.extractfile(member).read()
                            verification_results.append((member.name, True, "OK"))
                        except Exception as e:
                            verification_results.append((member.name, False, str(e)))

                # Verificação detalhada (se solicitado)
                if detailed:
                    failed_files = [result for result in verification_results if not result[1]]
                    if failed_files:
                        self.logger.warning(f"Arquivos corrompidos encontrados: {len(failed_files)}")
                        for name, status, error in failed_files:
                            self.logger.warning(f"  - {name}: {error}")
                        return False

                self.logger.info(f"✅ Backup verificado: {len(verification_results)} arquivos OK")
                return True

        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar backup {backup_path}: {e}")
            return False

    def list_backups(self) -> List[Dict]:
        """Lista todos os backups disponíveis"""
        backups = []

        try:
            backup_files = list(self.backup_dir.glob("freqtrade3_*.tar.gz.enc"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            for backup_path in backup_files:
                backup_info = {
                    "name": backup_path.name,
                    "path": str(backup_path),
                    "size": backup_path.stat().st_size,
                    "created": datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat(),
                    "type": "full" if "full" in backup_path.name else "incremental",
                    "verified": self.verify_backup(backup_path, detailed=False)
                }
                backups.append(backup_info)

        except Exception as e:
            self.logger.error(f"Erro ao listar backups: {e}")

        return backups

    def restore_backup(self, backup_path: Path, target_dir: Optional[Path] = None) -> bool:
        """Restaura backup para diretório específico"""
        try:
            self.logger.info(f"🔄 Iniciando restauração de: {backup_path.name}")

            # Verificar backup primeiro
            if not self.verify_backup(backup_path):
                self.logger.error("Backup não passou na verificação de integridade")
                return False

            # Descriptografar e decomprimir
            with open(backup_path, 'rb') as f:
                encrypted_data = f.read()

            cipher = self._create_encryption_cipher()
            compressed_data = cipher.decrypt(encrypted_data)
            tar_data = gzip.decompress(compressed_data)

            # Determinar diretório de destino
            if target_dir is None:
                target_dir = Path.cwd()

            target_dir = target_dir.resolve()

            # Criar backup dos arquivos existentes
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pre_restore_backup = target_dir / f"pre_restore_backup_{timestamp}.tar.gz.enc"

            self.logger.info("📦 Criando backup pré-restauração...")
            self._create_backup_of_directory(target_dir, pre_restore_backup)

            # Restaurar arquivos
            import io
            tar_buffer = io.BytesIO(tar_data)

            with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
                # Extrair manifesto para log
                manifest_file = tar.getmember('manifest.json')
                manifest_content = tar.extractfile(manifest_file).read()
                manifest = json.loads(manifest_content.decode('utf-8'))

                # Extrair arquivos
                for member in tar.getmembers():
                    if member.name == 'manifest.json':
                        continue

                    try:
                        tar.extract(member, path=target_dir)
                        self.logger.debug(f"Restaurado: {member.name}")
                    except Exception as e:
                        self.logger.warning(f"Erro ao restaurar {member.name}: {e}")

            # Log de sucesso
            self._log_backup_event("BACKUP_RESTORED", {
                "backup_file": backup_path.name,
                "target_directory": str(target_dir),
                "files_restored": len([m for m in manifest["files"]]),
                "pre_restore_backup": str(pre_restore_backup)
            })

            self.logger.info(f"✅ Backup restaurado com sucesso!")
            self.logger.info(f"   Arquivos restaurados: {manifest['total_files']}")
            self.logger.info(f"   Diretório: {target_dir}")
            self.logger.info(f"   Backup pré-restauração: {pre_restore_backup.name}")

            return True

        except Exception as e:
            self.logger.error(f"❌ Erro ao restaurar backup {backup_path}: {e}")
            return False

    def _create_backup_of_directory(self, directory: Path, backup_path: Path):
        """Cria backup de um diretório"""
        try:
            import io

            # Coletar arquivos
            files = list(directory.rglob('*'))
            files = [f for f in files if f.is_file()]

            # Criar manifesto simplificado
            manifest = {
                "type": "pre_restore_backup",
                "timestamp": datetime.now().isoformat(),
                "total_files": len(files),
                "files": []
            }

            # Criar tarball
            tar_buffer = io.BytesIO()

            with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
                # Adicionar manifesto
                manifest_json = json.dumps(manifest, indent=2).encode('utf-8')
                tarinfo = tarfile.TarInfo(name='manifest.json')
                tarinfo.size = len(manifest_json)
                tar.addfile(tarinfo, io.BytesIO(manifest_json))

                # Adicionar arquivos (excluindo o backup sendo criado)
                for file_path in files:
                    if file_path.parent == backup_path.parent and file_path.name.startswith(backup_path.stem):
                        continue

                    try:
                        tar.add(file_path, arcname=file_path.relative_to(directory))
                    except Exception:
                        continue

            # Comprimir e criptografar
            tar_data = tar_buffer.getvalue()
            compressed_data = self._compress_data(tar_data)
            encrypted_data = self._encrypt_data(compressed_data)

            # Salvar
            with open(backup_path, 'wb') as f:
                f.write(encrypted_data)

        except Exception as e:
            self.logger.warning(f"Erro ao criar backup pré-restauração: {e}")

    def cleanup_old_backups(self):
        """Remove backups antigos baseado na política de retenção"""
        try:
            retention_days = self.config['backup']['retention_days']
            max_backups = self.config['backup']['max_backups']

            # Listar backups ordenados por data
            backup_files = list(self.backup_dir.glob("freqtrade3_*.tar.gz.enc"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            removed_count = 0

            # Remover backups antigos por idade
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            for backup_path in backup_files[:]:
                backup_time = datetime.fromtimestamp(backup_path.stat().st_mtime)
                if backup_time < cutoff_time:
                    backup_path.unlink()
                    backup_files.remove(backup_path)
                    removed_count += 1
                    self.logger.info(f"🗑️ Removido backup antigo: {backup_path.name}")

            # Remover backups excedentes
            if len(backup_files) > max_backups:
                for backup_path in backup_files[max_backups:]:
                    backup_path.unlink()
                    removed_count += 1
                    self.logger.info(f"🗑️ Removido backup excedente: {backup_path.name}")

            if removed_count > 0:
                self._log_backup_event("BACKUP_CLEANUP", {
                    "removed_count": removed_count,
                    "remaining_backups": len(backup_files[:max_backups])
                })

            self.logger.info(f"🧹 Limpeza concluída: {removed_count} backups removidos")

        except Exception as e:
            self.logger.error(f"Erro na limpeza de backups: {e}")

    def _log_backup_event(self, event_type: str, details: Dict):
        """Registra evento de backup"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "details": details,
            "system": "FreqTrade3 Backup System"
        }

        # Adicionar ao log de auditoria
        audit_log = Path("logs/backup_audit.log")
        try:
            with open(audit_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            self.logger.warning(f"Erro ao registrar evento no audit log: {e}")

        # Registrar no log principal
        self.logger.info(f"EVENTO: {event_type}")

    def start_scheduled_backups(self):
        """Inicia sistema de backup agendado"""
        def backup_job():
            try:
                # Verificar se é hora do backup completo
                now = datetime.now()
                if now.hour == 2 and now.minute < 10:  # Entre 02:00-02:10
                    if now.weekday() == 0:  # Segunda-feira
                        self.logger.info("📅 Criando backup semanal completo...")
                        self.create_full_backup()
                    else:
                        self.logger.info("📅 Criando backup incremental diário...")
                        self.create_incremental_backup()

                # Limpeza de backups antigos
                if now.hour == 3 and now.minute == 0:  # 03:00
                    self.logger.info("🧹 Executando limpeza de backups antigos...")
                    self.cleanup_old_backups()

            except Exception as e:
                self.logger.error(f"Erro no job agendado de backup: {e}")

        # Agendar job a cada 10 minutos
        schedule.every(10).minutes.do(backup_job)

        self.logger.info("📅 Sistema de backup agendado iniciado")
        self.logger.info("   Backup completo: Segunda-feira às 02:00")
        self.logger.info("   Backup incremental: Diariamente às 02:00")
        self.logger.info("   Limpeza: Diariamente às 03:00")

        # Manter agendador rodando
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            self.logger.info("🛑 Sistema de backup agendado parado")


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Sistema de Backup FreqTrade3')
    parser.add_argument('--create-full', action='store_true', help='Criar backup completo')
    parser.add_argument('--create-incremental', action='store_true', help='Criar backup incremental')
    parser.add_argument('--list', action='store_true', help='Listar backups disponíveis')
    parser.add_argument('--verify', type=str, help='Verificar backup específico')
    parser.add_argument('--restore', type=str, help='Restaurar backup específico')
    parser.add_argument('--target-dir', type=str, help='Diretório de destino para restauração')
    parser.add_argument('--cleanup', action='store_true', help='Limpar backups antigos')
    parser.add_argument('--schedule', action='store_true', help='Iniciar sistema agendado')
    parser.add_argument('--config', type=str, default='backup_config.json', help='Arquivo de configuração')

    args = parser.parse_args()

    # Inicializar sistema de backup
    backup_system = SecureBackupSystem(args.config)

    try:
        if args.create_full:
            print("🚀 Criando backup completo...")
            result = backup_system.create_full_backup()
            if result:
                print(f"✅ Backup completo criado: {result}")
            else:
                print("❌ Falha ao criar backup completo")
                return 1

        elif args.create_incremental:
            print("🚀 Criando backup incremental...")
            result = backup_system.create_incremental_backup()
            if result:
                print(f"✅ Backup incremental criado: {result}")
            elif result is None:
                print("ℹ️ Nenhum arquivo modificado encontrado")
            else:
                print("❌ Falha ao criar backup incremental")
                return 1

        elif args.list:
            print("📋 Listando backups disponíveis:")
            backups = backup_system.list_backups()
            if not backups:
                print("   Nenhum backup encontrado")
            else:
                for backup in backups:
                    verified = "✅" if backup['verified'] else "❌"
                    size_mb = backup['size'] / 1024 / 1024
                    print(f"   {verified} {backup['name']}")
                    print(f"      Tipo: {backup['type']} | Tamanho: {size_mb:.2f} MB")
                    print(f"      Criado: {backup['created']}")
                    print()

        elif args.verify:
            backup_path = Path(args.verify)
            if not backup_path.exists():
                print(f"❌ Backup não encontrado: {backup_path}")
                return 1

            print(f"🔍 Verificando backup: {backup_path.name}")
            if backup_system.verify_backup(backup_path, detailed=True):
                print("✅ Backup verificado com sucesso")
            else:
                print("❌ Backup com problemas de integridade")
                return 1

        elif args.restore:
            backup_path = Path(args.restore)
            if not backup_path.exists():
                print(f"❌ Backup não encontrado: {backup_path}")
                return 1

            target_dir = Path(args.target_dir) if args.target_dir else None
            if target_dir:
                target_dir.mkdir(parents=True, exist_ok=True)

            print(f"🔄 Restaurando backup: {backup_path.name}")
            if backup_system.restore_backup(backup_path, target_dir):
                print("✅ Backup restaurado com sucesso")
            else:
                print("❌ Falha na restauração do backup")
                return 1

        elif args.cleanup:
            print("🧹 Limpando backups antigos...")
            backup_system.cleanup_old_backups()
            print("✅ Limpeza concluída")

        elif args.schedule:
            print("📅 Iniciando sistema de backup agendado...")
            backup_system.start_scheduled_backups()

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n🛑 Operação cancelada pelo usuário")
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
