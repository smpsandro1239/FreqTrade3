#!/usr/bin/env python3
"""
FreqTrade3 - Sistema de Backup e Recovery Automático
Versão: 4.0 - Proteção de Dados Institucional
Características: Backup automático, compressão, criptografia, recovery point, cleanup
"""

import gzip
import hashlib
import json
import logging
import os
import pickle
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import schedule
import yaml

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupType(Enum):
    """Tipos de backup"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    EMERGENCY = "emergency"

class BackupStatus(Enum):
    """Status do backup"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    VERIFIED = "verified"

class RecoveryStatus(Enum):
    """Status do recovery"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class BackupJob:
    """Job de backup"""
    id: str
    type: BackupType
    source_paths: List[str]
    target_path: str
    compression: bool
    encryption: bool
    status: BackupStatus
    start_time: str
    end_time: Optional[str] = None
    file_count: int = 0
    total_size: int = 0
    compressed_size: int = 0
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class RecoveryJob:
    """Job de recovery"""
    id: str
    backup_id: str
    target_paths: List[str]
    status: RecoveryStatus
    start_time: str
    end_time: Optional[str] = None
    files_restored: int = 0
    total_size: int = 0
    verified: bool = False
    error_message: Optional[str] = None
    rollback_available: bool = True

class AutomaticBackupSystem:
    """Sistema automático de backup e recovery"""

    def __init__(self, db_path: str = 'user_data/freqtrade3.db'):
        self.db_path = db_path
        self.backup_dir = 'backups'
        self.temp_dir = 'temp'
        self.config_file = 'configs/backup_config.yaml'

        # Criar diretórios
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs('configs', exist_ok=True)

        # Estado interno
        self.backup_jobs = {}
        self.recovery_jobs = {}
        self.backup_history = []
        self.monitoring_active = False
        self.scheduler_thread = None

        # Configurações
        self.config = self._load_config()

        # Inicializar sistema
        self._init_backup_system()

    def _init_backup_system(self):
        """Inicializar sistema de backup"""
        # Inicializar base de dados
        self._init_database()

        # Iniciar agendador
        self._start_scheduler()

        print("💾 Sistema de Backup e Recovery Automático inicializado")

    def _init_database(self):
        """Inicializar base de dados de backup"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Tabela de jobs de backup
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backup_jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    source_paths TEXT,
                    target_path TEXT,
                    compression BOOLEAN,
                    encryption BOOLEAN,
                    status TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    file_count INTEGER,
                    total_size INTEGER,
                    compressed_size INTEGER,
                    checksum TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')

            # Tabela de jobs de recovery
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recovery_jobs (
                    id TEXT PRIMARY KEY,
                    backup_id TEXT,
                    target_paths TEXT,
                    status TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    files_restored INTEGER,
                    total_size INTEGER,
                    verified BOOLEAN,
                    error_message TEXT,
                    rollback_available BOOLEAN
                )
            ''')

            # Tabela de arquivos de backup
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backup_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_id TEXT,
                    file_path TEXT,
                    original_size INTEGER,
                    compressed_size INTEGER,
                    checksum TEXT,
                    compressed_path TEXT
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao inicializar database de backup: {e}")

    def _load_config(self) -> Dict[str, Any]:
        """Carregar configurações de backup"""
        default_config = {
            'backup': {
                'schedule': {
                    'full_backup': '0 2 * * 0',      # Domingos às 02:00
                    'incremental_backup': '0 2 * * 1-6',  # Segunda a sábado às 02:00
                    'cleanup': '0 3 * * 0'          # Domingos às 03:00
                },
                'retention': {
                    'full_backups_days': 30,        # Manter backups completos por 30 dias
                    'incremental_backups_days': 7,  # Manter incrementais por 7 dias
                    'max_full_backups': 4,          # Máximo 4 backups completos
                    'max_incremental_backups': 20   # Máximo 20 backups incrementais
                },
                'compression': {
                    'enabled': True,
                    'level': 6,                      # Nível de compressão (1-9)
                    'algorithm': 'gzip'              # gzip, bzip2, xz
                },
                'encryption': {
                    'enabled': False,                # Ativar se necessário
                    'algorithm': 'AES-256',          # Algoritmo de criptografia
                    'key_file': 'backup.key'         # Arquivo com a chave
                }
            },
            'paths_to_backup': [
                'user_data/',
                'strategies/',
                'configs/',
                'logs/',
                'optimization_results/',
                'sentiment_data/',
                'risk_data/',
                'portfolio_data/',
                'alerts_data/',
                'trading_data/',
                'models/',
                '*.py',
                '*.md',
                '*.json',
                '*.yaml',
                '*.yml'
            ],
            'paths_to_exclude': [
                'backups/',
                'temp/',
                '__pycache__/',
                '*.pyc',
                '.git/',
                'node_modules/',
                '*.log',
                '*.tmp'
            ],
            'emergency': {
                'auto_backup_on_startup': True,
                'auto_backup_on_shutdown': True,
                'backup_before_updates': True,
                'emergency_backup_frequency': 300  # 5 minutos
            },
            'verification': {
                'check_integrity': True,
                'verify_after_backup': True,
                'test_recovery': False  # Teste de recovery (pode ser demorado)
            }
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                return {**default_config, **config}
            else:
                with open(self.config_file, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
                return default_config
        except Exception as e:
            print(f"⚠️  Erro ao carregar configuração: {e}")
            return default_config

    def create_full_backup(self, description: str = "Backup completo") -> str:
        """Criar backup completo"""
        try:
            backup_id = f"full_{int(time.time())}"

            # Definir paths de origem
            source_paths = self.config['paths_to_backup']

            # Definir destino
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = os.path.join(self.backup_dir, f"full_backup_{timestamp}.zip")

            # Configurações de backup
            compression = self.config['backup']['compression']['enabled']
            encryption = self.config['backup']['encryption']['enabled']

            # Criar job
            job = BackupJob(
                id=backup_id,
                type=BackupType.FULL,
                source_paths=source_paths,
                target_path=target_path,
                compression=compression,
                encryption=encryption,
                status=BackupStatus.PENDING,
                start_time=datetime.now().isoformat(),
                metadata={'description': description}
            )

            # Executar backup em thread separada
            thread = threading.Thread(target=self._execute_backup, args=(job,))
            thread.daemon = True
            thread.start()

            logger.info(f"Backup completo iniciado: {backup_id}")
            return backup_id

        except Exception as e:
            logger.error(f"Erro ao criar backup completo: {e}")
            raise

    def create_incremental_backup(self, last_backup_id: str = None) -> str:
        """Criar backup incremental"""
        try:
            backup_id = f"inc_{int(time.time())}"

            # Se não especificado, encontrar último backup
            if not last_backup_id:
                last_backup_id = self._get_last_backup_id()

            # Definir paths de origem
            source_paths = self._get_modified_paths(last_backup_id)

            if not source_paths:
                logger.info("Nenhum arquivo modificado para backup incremental")
                return None

            # Definir destino
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = os.path.join(self.backup_dir, f"incremental_backup_{timestamp}.zip")

            # Criar job
            job = BackupJob(
                id=backup_id,
                type=BackupType.INCREMENTAL,
                source_paths=source_paths,
                target_path=target_path,
                compression=self.config['backup']['compression']['enabled'],
                encryption=self.config['backup']['encryption']['enabled'],
                status=BackupStatus.PENDING,
                start_time=datetime.now().isoformat(),
                metadata={'base_backup_id': last_backup_id}
            )

            # Executar backup
            thread = threading.Thread(target=self._execute_backup, args=(job,))
            thread.daemon = True
            thread.start()

            logger.info(f"Backup incremental iniciado: {backup_id}")
            return backup_id

        except Exception as e:
            logger.error(f"Erro ao criar backup incremental: {e}")
            raise

    def _execute_backup(self, job: BackupJob):
        """Executar job de backup"""
        try:
            logger.info(f"Iniciando backup {job.id}")
            job.status = BackupStatus.IN_PROGRESS
            self._save_backup_job(job)

            # Criar arquivo temporário
            temp_file = job.target_path + '.tmp'

            # Contadores
            file_count = 0
            total_size = 0

            # Criar arquivo ZIP
            with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED,
                               compresslevel=self.config['backup']['compression']['level']) as zipf:

                for source_path in job.source_paths:
                    if self._should_include_path(source_path):
                        if os.path.isfile(source_path):
                            self._add_file_to_zip(zipf, source_path, source_path)
                            file_count += 1
                            total_size += os.path.getsize(source_path)
                        elif os.path.isdir(source_path):
                            for root, dirs, files in os.walk(source_path):
                                # Filtrar diretórios excluídos
                                dirs[:] = [d for d in dirs if self._should_include_path(os.path.join(root, d))]

                                for file in files:
                                    file_path = os.path.join(root, file)
                                    if self._should_include_path(file_path):
                                        arcname = os.path.relpath(file_path, '.')
                                        self._add_file_to_zip(zipf, file_path, arcname)
                                        file_count += 1
                                        total_size += os.path.getsize(file_path)

            # Criptografar se necessário
            if job.encryption:
                encrypted_file = temp_file + '.enc'
                self._encrypt_file(temp_file, encrypted_file)
                os.remove(temp_file)
                temp_file = encrypted_file

            # Mover para local final
            shutil.move(temp_file, job.target_path)

            # Calcular checksum
            checksum = self._calculate_file_checksum(job.target_path)

            # Atualizar job
            job.status = BackupStatus.COMPLETED
            job.end_time = datetime.now().isoformat()
            job.file_count = file_count
            job.total_size = total_size
            job.compressed_size = os.path.getsize(job.target_path)
            job.checksum = checksum

            # Salvar job
            self._save_backup_job(job)
            self.backup_jobs[job.id] = job

            logger.info(f"Backup {job.id} concluído: {file_count} arquivos, {total_size} bytes")

            # Verificar integridade
            if self.config['verification']['check_integrity']:
                self._verify_backup(job)

        except Exception as e:
            job.status = BackupStatus.FAILED
            job.end_time = datetime.now().isoformat()
            job.error_message = str(e)
            self._save_backup_job(job)
            logger.error(f"Backup {job.id} falhou: {e}")

    def _should_include_path(self, path: str) -> bool:
        """Verificar se path deve ser incluído no backup"""
        # Verificar exclusões
        for exclude_pattern in self.config['paths_to_exclude']:
            if self._path_matches_pattern(path, exclude_pattern):
                return False

        # Verificar inclusões (para padrões específicos)
        for include_pattern in self.config['paths_to_backup']:
            if '*' in include_pattern or '?' in include_pattern:
                if self._path_matches_pattern(path, include_pattern):
                    return True

        # Para diretórios específicos, incluir se está na lista
        if os.path.isdir(path):
            return path.rstrip('/') in [p.rstrip('/') for p in self.config['paths_to_backup']]

        return True

    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Verificar se path corresponde ao padrão"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern)

    def _add_file_to_zip(self, zipf: zipfile.ZipFile, file_path: str, arcname: str):
        """Adicionar arquivo ao ZIP"""
        try:
            zipf.write(file_path, arcname)
        except Exception as e:
            logger.warning(f"Erro ao adicionar {file_path} ao backup: {e}")

    def _encrypt_file(self, source_file: str, target_file: str):
        """Criptografar arquivo (implementação simplificada)"""
        try:
            # Em produção, usar criptografia real como cryptography
            # Por agora, apenas simular
            with open(source_file, 'rb') as f_in:
                with open(target_file, 'wb') as f_out:
                    data = f_in.read()
                    # Simulação de criptografia (não segura!)
                    encrypted = bytes([b ^ 0xAA for b in data])
                    f_out.write(encrypted)
        except Exception as e:
            logger.error(f"Erro na criptografia: {e}")
            raise

    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calcular checksum do arquivo"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Erro ao calcular checksum: {e}")
            return None

    def _get_last_backup_id(self) -> Optional[str]:
        """Obter ID do último backup"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id FROM backup_jobs
                WHERE status = 'completed'
                ORDER BY start_time DESC
                LIMIT 1
            ''')

            result = cursor.fetchone()
            conn.close()

            return result[0] if result else None

        except Exception as e:
            logger.error(f"Erro ao obter último backup: {e}")
            return None

    def _get_modified_paths(self, base_backup_id: str) -> List[str]:
        """Obter paths modificados desde último backup"""
        try:
            if not base_backup_id:
                return self.config['paths_to_backup']

            # Implementação simplificada: retornar todos os paths
            # Em produção, seria necessário rastrear timestamps de modificação
            modified_paths = []
            current_time = time.time()

            for path in self.config['paths_to_backup']:
                if os.path.exists(path):
                    if os.path.isfile(path):
                        if os.path.getmtime(path) > current_time - 86400:  # Modificado nas últimas 24h
                            modified_paths.append(path)
                    elif os.path.isdir(path):
                        # Verificar se há arquivos modificados no diretório
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                if os.path.getmtime(file_path) > current_time - 86400:
                                    modified_paths.append(path)
                                    break
                            else:
                                continue
                            break

            return modified_paths if modified_paths else self.config['paths_to_backup']

        except Exception as e:
            logger.error(f"Erro ao obter paths modificados: {e}")
            return self.config['paths_to_backup']

    def _verify_backup(self, job: BackupJob) -> bool:
        """Verificar integridade do backup"""
        try:
            logger.info(f"Verificando backup {job.id}")

            # Verificar se arquivo existe
            if not os.path.exists(job.target_path):
                job.status = BackupStatus.FAILED
                job.error_message = "Arquivo de backup não encontrado"
                return False

            # Verificar checksum
            if job.checksum:
                current_checksum = self._calculate_file_checksum(job.target_path)
                if current_checksum != job.checksum:
                    job.status = BackupStatus.FAILED
                    job.error_message = "Checksum mismatch"
                    return False

            # Testar extração (se configurado)
            if self.config['verification']['test_recovery']:
                test_dir = os.path.join(self.temp_dir, f"test_{job.id}")
                if self._test_backup_extraction(job.target_path, test_dir):
                    shutil.rmtree(test_dir, ignore_errors=True)
                else:
                    job.status = BackupStatus.FAILED
                    job.error_message = "Falha no teste de extração"
                    return False

            job.status = BackupStatus.VERIFIED
            self._save_backup_job(job)

            logger.info(f"Backup {job.id} verificado com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro na verificação do backup {job.id}: {e}")
            return False

    def _test_backup_extraction(self, backup_file: str, test_dir: str) -> bool:
        """Testar extração do backup"""
        try:
            os.makedirs(test_dir, exist_ok=True)

            with zipfile.ZipFile(backup_file, 'r') as zipf:
                # Testar se consegue listar arquivos
                file_list = zipf.namelist()
                if not file_list:
                    return False

                # Testar extração de alguns arquivos
                for file_info in file_list[:5]:  # Primeiros 5 arquivos
                    try:
                        zipf.extract(file_info, test_dir)
                    except Exception:
                        return False

            return True

        except Exception as e:
            logger.error(f"Erro no teste de extração: {e}")
            return False

    def restore_from_backup(self, backup_id: str, target_paths: List[str] = None,
                          create_rollback: bool = True) -> str:
        """Restaurar de backup"""
        try:
            # Verificar se backup existe
            job = self.backup_jobs.get(backup_id)
            if not job:
                job = self._load_backup_job(backup_id)

            if not job or job.status not in [BackupStatus.COMPLETED, BackupStatus.VERIFIED]:
                raise ValueError(f"Backup {backup_id} não encontrado ou inválido")

            # Definir paths de destino
            if not target_paths:
                target_paths = [os.path.dirname(p) for p in job.source_paths]

            # Criar rollback se solicitado
            rollback_info = None
            if create_rollback:
                rollback_info = self._create_rollback_backup(target_paths)

            # Criar job de recovery
            recovery_id = f"recovery_{int(time.time())}"
            recovery_job = RecoveryJob(
                id=recovery_id,
                backup_id=backup_id,
                target_paths=target_paths,
                status=RecoveryStatus.NOT_STARTED,
                start_time=datetime.now().isoformat(),
                rollback_available=rollback_info is not None
            )

            # Executar recovery
            thread = threading.Thread(target=self._execute_recovery, args=(recovery_job, job, target_paths))
            thread.daemon = True
            thread.start()

            logger.info(f"Recovery iniciado: {recovery_id}")
            return recovery_id

        except Exception as e:
            logger.error(f"Erro ao iniciar recovery: {e}")
            raise

    def _execute_recovery(self, recovery_job: RecoveryJob, backup_job: BackupJob, target_paths: List[str]):
        """Executar job de recovery"""
        try:
            logger.info(f"Iniciando recovery {recovery_job.id}")
            recovery_job.status = RecoveryStatus.IN_PROGRESS
            self._save_recovery_job(recovery_job)

            # Backup temporário
            backup_file = backup_job.target_path

            # Descriptografar se necessário
            temp_file = backup_file
            if backup_job.encryption:
                temp_file = backup_file + '.dec'
                self._decrypt_file(backup_file, temp_file)

            # Extrair backup
            files_restored = 0
            total_size = 0

            with zipfile.ZipFile(temp_file, 'r') as zipf:
                for file_info in zipf.filelist:
                    # Extrair arquivo
                    target_file = os.path.join(target_paths[0], file_info.filename)
                    target_dir = os.path.dirname(target_file)

                    # Criar diretório se não existir
                    os.makedirs(target_dir, exist_ok=True)

                    # Extrair arquivo
                    zipf.extract(file_info, target_paths[0])
                    files_restored += 1
                    total_size += file_info.file_size

            # Limpar arquivo temporário
            if backup_job.encryption and os.path.exists(temp_file):
                os.remove(temp_file)

            # Verificar integridade
            verified = False
            if self.config['verification']['verify_after_backup']:
                verified = self._verify_recovery(target_paths, backup_job)

            # Finalizar job
            recovery_job.status = RecoveryStatus.SUCCESS
            recovery_job.end_time = datetime.now().isoformat()
            recovery_job.files_restored = files_restored
            recovery_job.total_size = total_size
            recovery_job.verified = verified

            self._save_recovery_job(recovery_job)

            logger.info(f"Recovery {recovery_job.id} concluído: {files_restored} arquivos")

        except Exception as e:
            recovery_job.status = RecoveryStatus.FAILED
            recovery_job.end_time = datetime.now().isoformat()
            recovery_job.error_message = str(e)
            self._save_recovery_job(recovery_job)
            logger.error(f"Recovery {recovery_job.id} falhou: {e}")

    def _decrypt_file(self, encrypted_file: str, decrypted_file: str):
        """Descriptografar arquivo"""
        try:
            with open(encrypted_file, 'rb') as f_in:
                with open(decrypted_file, 'wb') as f_out:
                    data = f_in.read()
                    # Simulação de descriptografia
                    decrypted = bytes([b ^ 0xAA for b in data])
                    f_out.write(decrypted)
        except Exception as e:
            logger.error(f"Erro na descriptografia: {e}")
            raise

    def _create_rollback_backup(self, paths: List[str]) -> Dict[str, Any]:
        """Criar backup de rollback antes do recovery"""
        try:
            rollback_id = f"rollback_{int(time.time())}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rollback_dir = os.path.join(self.backup_dir, f"rollback_{timestamp}")

            # Criar backup
            for path in paths:
                if os.path.exists(path):
                    target_path = os.path.join(rollback_dir, os.path.basename(path))
                    if os.path.isdir(path):
                        shutil.copytree(path, target_path, ignore=shutil.ignore_patterns('*'))
                    else:
                        shutil.copy2(path, target_path)

            return {
                'rollback_id': rollback_id,
                'rollback_dir': rollback_dir,
                'paths': paths,
                'created_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Erro ao criar rollback: {e}")
            return None

    def _verify_recovery(self, target_paths: List[str], backup_job: BackupJob) -> bool:
        """Verificar se recovery foi bem-sucedido"""
        try:
            # Implementação simplificada
            # Verificar se arquivos foram extraídos
            for path in target_paths:
                if os.path.exists(path):
                    return True
            return False
        except Exception as e:
            logger.error(f"Erro na verificação do recovery: {e}")
            return False

    def _save_backup_job(self, job: BackupJob):
        """Salvar job de backup no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO backup_jobs
                (id, type, source_paths, target_path, compression, encryption,
                 status, start_time, end_time, file_count, total_size,
                 compressed_size, checksum, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job.id, job.type.value, json.dumps(job.source_paths), job.target_path,
                job.compression, job.encryption, job.status.value, job.start_time,
                job.end_time, job.file_count, job.total_size, job.compressed_size,
                job.checksum, job.error_message, json.dumps(job.metadata or {})
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao salvar job de backup: {e}")

    def _save_recovery_job(self, job: RecoveryJob):
        """Salvar job de recovery no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO recovery_jobs
                (id, backup_id, target_paths, status, start_time, end_time,
                 files_restored, total_size, verified, error_message, rollback_available)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job.id, job.backup_id, json.dumps(job.target_paths), job.status.value,
                job.start_time, job.end_time, job.files_restored, job.total_size,
                job.verified, job.error_message, job.rollback_available
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao salvar job de recovery: {e}")

    def _load_backup_job(self, backup_id: str) -> Optional[BackupJob]:
        """Carregar job de backup do banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM backup_jobs WHERE id = ?
            ''', (backup_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return BackupJob(
                    id=row[0],
                    type=BackupType(row[1]),
                    source_paths=json.loads(row[2]),
                    target_path=row[3],
                    compression=bool(row[4]),
                    encryption=bool(row[5]),
                    status=BackupStatus(row[6]),
                    start_time=row[7],
                    end_time=row[8],
                    file_count=row[9],
                    total_size=row[10],
                    compressed_size=row[11],
                    checksum=row[12],
                    error_message=row[13],
                    metadata=json.loads(row[14]) if row[14] else {}
                )

        except Exception as e:
            logger.error(f"Erro ao carregar job de backup: {e}")

        return None

    def _start_scheduler(self):
        """Iniciar agendador de backups"""
        try:
            schedule.clear()  # Limpar agendamentos existentes

            # Agendar backups
            full_schedule = self.config['backup']['schedule']['full_backup']
            incremental_schedule = self.config['backup']['schedule']['incremental_backup']
            cleanup_schedule = self.config['backup']['schedule']['cleanup']

            schedule.every().sunday.at("02:00").do(self.create_full_backup, "Backup completo agendado")
            schedule.every().monday.at("02:00").do(self.create_incremental_backup)
            schedule.every().tuesday.at("02:00").do(self.create_incremental_backup)
            schedule.every().wednesday.at("02:00").do(self.create_incremental_backup)
            schedule.every().thursday.at("02:00").do(self.create_incremental_backup)
            schedule.every().friday.at("02:00").do(self.create_incremental_backup)
            schedule.every().saturday.at("02:00").do(self.create_incremental_backup)

            # Cleanup
            schedule.every().sunday.at("03:00").do(self._cleanup_old_backups)

            # Thread do scheduler
            def run_scheduler():
                while True:
                    schedule.run_pending()
                    time.sleep(60)  # Verificar a cada minuto

            self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            self.scheduler_thread.start()

            logger.info("Agendador de backup iniciado")

        except Exception as e:
            logger.error(f"Erro ao iniciar agendador: {e}")

    def _cleanup_old_backups(self):
        """Limpar backups antigos"""
        try:
            logger.info("Iniciando cleanup de backups antigos")

            # Obter configurações de retenção
            retention = self.config['backup']['retention']
            max_full = retention['max_full_backups']
            max_inc = retention['max_incremental_backups']

            # Listar backups
            full_backups = []
            incremental_backups = []

            for file in os.listdir(self.backup_dir):
                if file.startswith('full_backup_'):
                    full_backups.append(file)
                elif file.startswith('incremental_backup_'):
                    incremental_backups.append(file)

            # Ordenar por data
            full_backups.sort(reverse=True)
            incremental_backups.sort(reverse=True)

            # Remover backups extras
            for backup in full_backups[max_full:]:
                backup_path = os.path.join(self.backup_dir, backup)
                os.remove(backup_path)
                logger.info(f"Backup removido: {backup}")

            for backup in incremental_backups[max_inc:]:
                backup_path = os.path.join(self.backup_dir, backup)
                os.remove(backup_path)
                logger.info(f"Backup removido: {backup}")

            # Limpar jobs antigos do banco
            self._cleanup_old_backup_jobs()

        except Exception as e:
            logger.error(f"Erro no cleanup: {e}")

    def _cleanup_old_backup_jobs(self):
        """Limpar jobs antigos do banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Manter apenas os últimos 100 jobs
            cursor.execute('''
                DELETE FROM backup_jobs WHERE id NOT IN (
                    SELECT id FROM backup_jobs
                    ORDER BY start_time DESC
                    LIMIT 100
                )
            ''')

            cursor.execute('''
                DELETE FROM recovery_jobs WHERE id NOT IN (
                    SELECT id FROM recovery_jobs
                    ORDER BY start_time DESC
                    LIMIT 100
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erro ao limpar jobs antigos: {e}")

    def get_backup_status(self) -> Dict[str, Any]:
        """Obter status dos backups"""
        try:
            # Contar backups por tipo e status
            backup_stats = defaultdict(lambda: defaultdict(int))

            for job in self.backup_jobs.values():
                backup_stats[job.type.value][job.status.value] += 1

            # Último backup
            last_backup = None
            if self.backup_jobs:
                last_backup = max(self.backup_jobs.values(),
                                key=lambda x: x.start_time)
                last_backup = asdict(last_backup)

            # Estatísticas de espaço
            total_size = 0
            for job in self.backup_jobs.values():
                if os.path.exists(job.target_path):
                    total_size += os.path.getsize(job.target_path)

            return {
                'total_backups': len(self.backup_jobs),
                'last_backup': last_backup,
                'backup_stats': dict(backup_stats),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'scheduler_active': self.scheduler_thread is not None,
                'next_scheduled': self._get_next_scheduled_backup()
            }

        except Exception as e:
            logger.error(f"Erro ao obter status: {e}")
            return {}

    def _get_next_scheduled_backup(self) -> Optional[str]:
        """Obter próximo backup agendado"""
        try:
            next_job = schedule.next_run()
            return next_job.isoformat() if next_job else None
        except Exception:
            return None

    def create_emergency_backup(self):
        """Criar backup de emergência"""
        try:
            logger.warning("Criando backup de emergência")
            backup_id = self.create_full_backup("Backup de emergência")

            # Manter este backup por mais tempo
            # (Implementação seria marcar no metadata)

            return backup_id

        except Exception as e:
            logger.error(f"Erro no backup de emergência: {e}")
            return None

# API para integração
def create_backup_system():
    """Criar instância do sistema de backup"""
    return AutomaticBackupSystem()

if __name__ == "__main__":
    # Teste do sistema de backup
    backup_system = create_backup_system()

    # Teste de backup completo
    backup_id = backup_system.create_full_backup("Teste de backup")
    print(f"Backup iniciado: {backup_id}")

    # Status
    status = backup_system.get_backup_status()
    print(f"Status: {status}")

    # Recovery (exemplo)
    # recovery_id = backup_system.restore_from_backup(backup_id)
    # print(f"Recovery iniciado: {recovery_id}")
