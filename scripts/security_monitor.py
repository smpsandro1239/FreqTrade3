#!/usr/bin/env python3
"""
================================================================
FREQTRADE3 - SISTEMA DE MONITORAMENTO DE SEGURANÇA
================================================================

Sistema avançado de monitoramento e detecção de vulnerabilidades
para o FreqTrade3 - Monitora continuamente:
- Credenciais expostas
- Permissões inadequadas
- Tráfego de rede suspeito
- Configurações de segurança
- Logs de segurança
- Tentativas de acesso não autorizadas

Funcionalidades:
- Monitoramento em tempo real
- Alertas automáticos via webhooks
- Logs detalhados de segurança
- Correção automática de vulnerabilidades
- Relatórios de segurança

Uso:
    python3 security_monitor.py --continuous
    python3 security_monitor.py --scan-once
    python3 security_monitor.py --dashboard
"""

import hashlib
import ipaddress
import json
import logging
import os
import re
import signal
import smtplib
import socket
import ssl
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


class SecurityMonitor:
    """Monitor de Segurança Avançado para FreqTrade3"""

    def __init__(self, config_path: str = "configs/security_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.running = False
        self.vulnerabilities = []
        self.security_logs = []
        self.network_monitor = None
        self.audit_start_time = datetime.now()

        # Configurar logging de segurança
        self._setup_security_logging()

        # Patterns críticos para detecção
        self.sensitive_patterns = {
            'api_keys': [
                r'api[_-]?key["\s]*[:=]["\s]*([A-Za-z0-9]{20,})',
                r'secret[_-]?key["\s]*[:=]["\s]*([A-Za-z0-9+/]{20,})',
                r'client[_-]?secret["\s]*[:=]["\s]*([A-Za-z0-9+/]{20,})',
                r'access[_-]?token["\s]*[:=]["\s]*([A-Za-z0-9]{20,})'
            ],
            'passwords': [
                r'password["\s]*[:=]["\s]*([^"\n]{8,})',
                r'passwd["\s]*[:=]["\s]*([^"\n]{8,})',
                r'pwd["\s]*[:=]["\s]*([^"\n]{8,})'
            ],
            'private_keys': [
                r'-----BEGIN (RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----',
                r'private[_-]?key["\s]*[:=]["\s]*["\']?(.*?)["\']?',
                r'ssh[_-]?key["\s]*[:=]["\s]*["\']?(.*?)["\']?'
            ],
            'urls_sensitive': [
                r'https://[^/]*@[^/]*',
                r'ws://[^/]*@[^/]*',
                r'wss://[^/]*@[^/]*'
            ]
        }

        # IPs suspeitos conhecidos
        self.suspicious_ips = [
            '127.0.0.1',  # Local
            '0.0.0.0',    # Broadcaster
        ]

        # Portas suspeitas
        self.suspicious_ports = [22, 23, 80, 135, 139, 445, 1433, 3389]

    def _load_config(self) -> Dict:
        """Carrega configuração de segurança"""
        default_config = {
            "monitoring": {
                "enabled": True,
                "interval_seconds": 60,
                "real_time": True,
                "dashboard_port": 9090
            },
            "alerts": {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "to_addresses": []
                },
                "webhook": {
                    "enabled": False,
                    "url": "",
                    "timeout": 10
                },
                "telegram": {
                    "enabled": False,
                    "bot_token": "",
                    "chat_id": ""
                },
                "discord": {
                    "enabled": False,
                    "webhook_url": ""
                }
            },
            "security_checks": {
                "file_scanning": {
                    "enabled": True,
                    "recursive": True,
                    "exclude_dirs": [".git", "__pycache__", "node_modules", "venv"]
                },
                "network_monitoring": {
                    "enabled": True,
                    "log_connections": True,
                    "monitor_ports": [8080, 3000, 5000]
                },
                "config_validation": {
                    "enabled": True,
                    "check_permissions": True,
                    "check_exposed_secrets": True
                },
                "log_analysis": {
                    "enabled": True,
                    "analyze_freqtrade_logs": True,
                    "detect_attacks": True
                }
            },
            "response_actions": {
                "auto_block_ip": False,
                "auto_restart_services": False,
                "quarantine_suspicious_files": False,
                "backup_critical_files": True
            },
            "whitelist": {
                "ips": [],
                "domains": [],
                "files": []
            }
        }

        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # Merge com configurações padrão
                default_config.update(user_config)
        except Exception as e:
            self._log_security_event(f"Erro ao carregar configuração: {e}", "ERROR")

        return default_config

    def _setup_security_logging(self):
        """Configura sistema de logging de segurança"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Formatter personalizado para segurança
        formatter = logging.Formatter(
            '%(asctime)s - [SECURITY] - %(levelname)s - %(name)s - %(message)s'
        )

        # Handler para arquivo de log de segurança
        security_file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "security_monitor.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        security_file_handler.setFormatter(formatter)

        # Logger de segurança
        self.logger = logging.getLogger('SecurityMonitor')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(security_file_handler)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _log_security_event(self, message: str, level: str = "INFO"):
        """Registra evento de segurança"""
        timestamp = datetime.now().isoformat()
        event = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "source": "SecurityMonitor"
        }

        self.security_logs.append(event)

        # Log com nível apropriado
        if level == "CRITICAL":
            self.logger.critical(message)
        elif level == "ERROR":
            self.logger.error(message)
        elif level == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)

        # Enviar alerta se configurado
        if level in ["CRITICAL", "ERROR"]:
            self._send_alert(message, level)

    def _send_alert(self, message: str, level: str):
        """Envia alertas de segurança"""
        try:
            # Webhook
            if self.config['alerts']['webhook']['enabled']:
                self._send_webhook_alert(message, level)

            # Email
            if self.config['alerts']['email']['enabled']:
                self._send_email_alert(message, level)

            # Telegram
            if self.config['alerts']['telegram']['enabled']:
                self._send_telegram_alert(message, level)

            # Discord
            if self.config['alerts']['discord']['enabled']:
                self._send_discord_alert(message, level)

        except Exception as e:
            self._log_security_event(f"Erro ao enviar alerta: {e}", "ERROR")

    def _send_webhook_alert(self, message: str, level: str):
        """Envia alerta via webhook"""
        try:
            webhook_data = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
                "source": "FreqTrade3 Security Monitor",
                "system": socket.gethostname()
            }

            response = requests.post(
                self.config['alerts']['webhook']['url'],
                json=webhook_data,
                timeout=self.config['alerts']['webhook']['timeout']
            )
            response.raise_for_status()

        except Exception as e:
            self._log_security_event(f"Erro webhook: {e}", "WARNING")

    def _send_email_alert(self, message: str, level: str):
        """Envia alerta via email"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.config['alerts']['email']['username']
            msg['Subject'] = f"🚨 Alerta FreqTrade3 - {level}"

            body = f"""
Alerta de Segurança FreqTrade3

Nível: {level}
Mensagem: {message}
Timestamp: {datetime.now().isoformat()}
Hostname: {socket.gethostname()}

Ação Recomendada: Verifique imediatamente o sistema e logs de segurança.
            """

            msg.attach(MimeText(body, 'plain'))

            server = smtplib.SMTP(
                self.config['alerts']['email']['smtp_server'],
                self.config['alerts']['email']['smtp_port']
            )
            server.starttls()
            server.login(
                self.config['alerts']['email']['username'],
                self.config['alerts']['email']['password']
            )

            for to_addr in self.config['alerts']['email']['to_addresses']:
                msg['To'] = to_addr
                server.send_message(msg)
                del msg['To']

            server.quit()

        except Exception as e:
            self._log_security_event(f"Erro email: {e}", "WARNING")

    def _send_telegram_alert(self, message: str, level: str):
        """Envia alerta via Telegram"""
        try:
            emoji = "🔴" if level == "CRITICAL" else "🟡"
            text = f"{emoji} Alerta FreqTrade3\n\nNível: {level}\nMensagem: {message}\n\nHora: {datetime.now().strftime('%H:%M:%S')}"

            url = f"https://api.telegram.org/bot{self.config['alerts']['telegram']['bot_token']}/sendMessage"
            data = {
                "chat_id": self.config['alerts']['telegram']['chat_id'],
                "text": text,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

        except Exception as e:
            self._log_security_event(f"Erro Telegram: {e}", "WARNING")

    def _send_discord_alert(self, message: str, level: str):
        """Envia alerta via Discord"""
        try:
            color = 0xff0000 if level == "CRITICAL" else 0xffaa00
            embed = {
                "title": f"🚨 Alerta FreqTrade3 - {level}",
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "fields": [
                    {"name": "Hostname", "value": socket.gethostname(), "inline": True},
                    {"name": "Timestamp", "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "inline": True}
                ]
            }

            data = {
                "embeds": [embed],
                "username": "FreqTrade3 Security Monitor"
            }

            response = requests.post(
                self.config['alerts']['discord']['webhook_url'],
                json=data,
                timeout=10
            )
            response.raise_for_status()

        except Exception as e:
            self._log_security_event(f"Erro Discord: {e}", "WARNING")

    def scan_for_secrets(self, directory: str = ".") -> List[Dict]:
        """Escaneia arquivos em busca de credenciais expostas"""
        vulnerabilities = []

        try:
            for root, dirs, files in os.walk(directory):
                # Pular diretórios excluídos
                for exclude_dir in self.config['security_checks']['file_scanning']['exclude_dirs']:
                    if exclude_dir in dirs:
                        dirs.remove(exclude_dir)

                for file in files:
                    file_path = os.path.join(root, file)

                    # Pular arquivos binários grandes
                    if os.path.getsize(file_path) > 10 * 1024 * 1024:  # 10MB
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        # Verificar cada padrão sensível
                        for category, patterns in self.sensitive_patterns.items():
                            for pattern in patterns:
                                matches = re.finditer(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    vulnerability = {
                                        "type": "SECRET_EXPOSED",
                                        "category": category,
                                        "file": file_path,
                                        "line": content[:match.start()].count('\n') + 1,
                                        "pattern": pattern,
                                        "severity": "HIGH",
                                        "description": f"Potencial {category.replace('_', ' ')} exposta",
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    vulnerabilities.append(vulnerability)

                    except Exception as e:
                        # Arquivo pode ser binário ou ter problemas de encoding
                        continue

        except Exception as e:
            self._log_security_event(f"Erro no scan de secrets: {e}", "ERROR")

        return vulnerabilities

    def check_file_permissions(self) -> List[Dict]:
        """Verifica permissões inadequadas de arquivos"""
        vulnerabilities = []

        critical_files = [
            "configs/config.json",
            "user_data/secrets.json",
            ".env",
            "api_keys.txt",
            "secrets.txt"
        ]

        for file_path in critical_files:
            if os.path.exists(file_path):
                try:
                    stat = os.stat(file_path)
                    mode = stat.st_mode

                    # Verificar se o arquivo tem permissões muito permissivas
                    if mode & 0o077:  # Qualquer permissão para grupo/outros
                        vulnerability = {
                            "type": "PERMISSION_VULNERABILITY",
                            "file": file_path,
                            "current_permissions": oct(mode)[-3:],
                            "recommended_permissions": "600",
                            "severity": "HIGH",
                            "description": "Arquivo com permissões muito permissivas",
                            "timestamp": datetime.now().isoformat()
                        }
                        vulnerabilities.append(vulnerability)

                except Exception as e:
                    self._log_security_event(f"Erro ao verificar permissões de {file_path}: {e}", "WARNING")

        return vulnerabilities

    def monitor_network_connections(self) -> List[Dict]:
        """Monitora conexões de rede suspeitas"""
        suspicious_connections = []

        try:
            # Verificar conexões ativas
            if sys.platform.startswith('linux'):
                result = subprocess.run(['netstat', '-tuln'],
                                      capture_output=True, text=True, timeout=10)
                connections = result.stdout

                for line in connections.split('\n'):
                    if 'LISTEN' in line and ':' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            address = parts[3]
                            port = int(address.split(':')[-1])

                            # Verificar portas suspeitas
                            if port in self.suspicious_ports:
                                suspicious_connections.append({
                                    "type": "SUSPICIOUS_PORT",
                                    "port": port,
                                    "address": address,
                                    "description": f"Porta suspeita {port} em listen",
                                    "timestamp": datetime.now().isoformat()
                                })

            elif sys.platform.startswith('win'):
                result = subprocess.run(['netstat', '-an'],
                                      capture_output=True, text=True, timeout=10)
                connections = result.stdout

                for line in connections.split('\n'):
                    if 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            address = parts[1]
                            port = int(address.split(':')[-1])

                            if port in self.suspicious_ports:
                                suspicious_connections.append({
                                    "type": "SUSPICIOUS_PORT",
                                    "port": port,
                                    "address": address,
                                    "description": f"Porta suspeita {port} em listening",
                                    "timestamp": datetime.now().isoformat()
                                })

        except Exception as e:
            self._log_security_event(f"Erro no monitoramento de rede: {e}", "WARNING")

        return suspicious_connections

    def validate_configuration(self) -> List[Dict]:
        """Valida configurações de segurança"""
        issues = []

        config_files = [
            "configs/config_template_dryrun.json",
            "configs/config_template_production.json"
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)

                    # Verificar se dry_run está configurado corretamente
                    if config_file.endswith('production'):
                        if config.get('dry_run', True):
                            issues.append({
                                "type": "CONFIGURATION_VULNERABILITY",
                                "file": config_file,
                                "issue": "DRY_RUN_ENABLED_IN_PRODUCTION",
                                "severity": "CRITICAL",
                                "description": "Dry run ainda habilitado em configuração de produção",
                                "timestamp": datetime.now().isoformat()
                            })

                    # Verificar API keys expostas
                    if config.get('exchange', {}).get('key') and config['exchange']['key'] not in ['YOUR_API_KEY_HERE', '${BINANCE_API_KEY}']:
                        issues.append({
                            "type": "CONFIGURATION_VULNERABILITY",
                            "file": config_file,
                            "issue": "API_KEY_NOT_TEMPLATED",
                            "severity": "HIGH",
                            "description": "API key não está usando template/variavel de ambiente",
                            "timestamp": datetime.now().isoformat()
                        })

                except Exception as e:
                    issues.append({
                        "type": "CONFIGURATION_ERROR",
                        "file": config_file,
                        "issue": f"JSON_PARSE_ERROR: {str(e)}",
                        "severity": "HIGH",
                        "description": f"Erro ao validar configuração: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })

        return issues

    def analyze_logs(self) -> List[Dict]:
        """Analisa logs em busca de atividades suspeitas"""
        suspicious_activities = []

        log_files = [
            "logs/freqtrade.log",
            "logs/freqtrade3.log",
            "logs/security_monitor.log"
        ]

        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Procurar por padrões suspeitos
                    suspicious_patterns = [
                        r'Error.*API.*key',
                        r'Failed.*authentication',
                        r'Access.*denied',
                        r'Suspicious.*activity',
                        r'Failed.*login',
                        r'Too many requests',
                        r'Rate limit exceeded'
                    ]

                    for pattern in suspicious_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            suspicious_activities.append({
                                "type": "SUSPICIOUS_LOG_ACTIVITY",
                                "file": log_file,
                                "line": line_num,
                                "pattern": pattern,
                                "match": match.group(),
                                "description": "Atividade sospeita detectada nos logs",
                                "timestamp": datetime.now().isoformat()
                            })

                except Exception as e:
                    self._log_security_event(f"Erro ao analisar log {log_file}: {e}", "WARNING")

        return suspicious_activities

    def run_security_scan(self) -> Dict:
        """Executa scan completo de segurança"""
        self._log_security_event("Iniciando scan completo de segurança", "INFO")

        scan_results = {
            "timestamp": datetime.now().isoformat(),
            "hostname": socket.gethostname(),
            "vulnerabilities": [],
            "scan_duration_seconds": 0
        }

        start_time = time.time()

        try:
            # 1. Scan por secrets expostos
            self._log_security_event("Escaneando por credenciais expostas...", "INFO")
            secrets_vulns = self.scan_for_secrets()
            scan_results["vulnerabilities"].extend(secrets_vulns)

            # 2. Verificar permissões de arquivos
            self._log_security_event("Verificando permissões de arquivos...", "INFO")
            permission_vulns = self.check_file_permissions()
            scan_results["vulnerabilities"].extend(permission_vulns)

            # 3. Monitorar rede
            if self.config['security_checks']['network_monitoring']['enabled']:
                self._log_security_event("Monitorando conexões de rede...", "INFO")
                network_vulns = self.monitor_network_connections()
                scan_results["vulnerabilities"].extend(network_vulns)

            # 4. Validar configurações
            self._log_security_event("Validando configurações...", "INFO")
            config_vulns = self.validate_configuration()
            scan_results["vulnerabilities"].extend(config_vulns)

            # 5. Analisar logs
            if self.config['security_checks']['log_analysis']['enabled']:
                self._log_security_event("Analisando logs de sistema...", "INFO")
                log_vulns = self.analyze_logs()
                scan_results["vulnerabilities"].extend(log_vulns)

            # Calcular duração
            scan_results["scan_duration_seconds"] = time.time() - start_time

            # Log de resumo
            total_vulns = len(scan_results["vulnerabilities"])
            critical_vulns = len([v for v in scan_results["vulnerabilities"] if v.get("severity") == "CRITICAL"])

            if total_vulns > 0:
                self._log_security_event(f"Scan completo: {total_vulns} vulnerabilidades encontradas ({critical_vulns} críticas)", "WARNING")
            else:
                self._log_security_event("Scan completo: Nenhuma vulnerabilidade encontrada", "INFO")

        except Exception as e:
            self._log_security_event(f"Erro durante scan de segurança: {e}", "ERROR")
            scan_results["error"] = str(e)

        return scan_results

    def generate_security_report(self) -> str:
        """Gera relatório completo de segurança"""
        report = f"""
================================================================
FREQTRADE3 - RELATÓRIO DE SEGURANÇA
================================================================
Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Hostname: {socket.gethostname()}
Período: {self.audit_start_time.strftime('%Y-%m-%d %H:%M:%S')} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RESUMO:
- Total de eventos de segurança: {len(self.security_logs)}
- Vulnerabilidades detectadas: {len(self.vulnerabilities)}
- Status do sistema: {'CRÍTICO' if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities) else 'ESTÁVEL'}

VULNERABILIDADES POR SEVERIDADE:
        """

        # Agrupar por severidade
        severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
        for severity in severities:
            count = len([v for v in self.vulnerabilities if v.get('severity') == severity])
            if count > 0:
                report += f"\n- {severity}: {count}"

        # Detalhes das vulnerabilidades
        if self.vulnerabilities:
            report += "\n\nDETALHES DAS VULNERABILIDADES:\n"
            for i, vuln in enumerate(self.vulnerabilities, 1):
                report += f"""
{i}. TIPO: {vuln.get('type', 'UNKNOWN')}
   SEVERIDADE: {vuln.get('severity', 'UNKNOWN')}
   DESCRIÇÃO: {vuln.get('description', 'Sem descrição')}
   ARQUIVO: {vuln.get('file', 'N/A')}
   TIMESTAMP: {vuln.get('timestamp', 'N/A')}
"""

        # Recomendações
        report += "\n\nRECOMENDAÇÕES DE SEGURANÇA:\n"
        report += """
1. ⚠️ CRÍTICAS: Resolver imediatamente
2. 🔴 ALTAS: Resolver em 24 horas
3. 🟡 MÉDIAS: Resolver em 1 semana
4. 🟡 BAIXAS: Resolver em 1 mês

AÇÕES RECOMENDADAS:
- Revisar e rotacionar credenciais expostas
- Configurar alertas de segurança
- Implementar backup automático
- Monitorar logs regularmente
- Atualizar configurações de rede
        """

        return report

    def start_continuous_monitoring(self):
        """Inicia monitoramento contínuo"""
        self.running = True
        self._log_security_event("Iniciando monitoramento contínuo", "INFO")

        def monitor_loop():
            while self.running:
                try:
                    # Executar scan
                    scan_results = self.run_security_scan()
                    self.vulnerabilities.extend(scan_results.get("vulnerabilities", []))

                    # Aguardar intervalo configurado
                    interval = self.config['monitoring']['interval_seconds']
                    for _ in range(interval):
                        if not self.running:
                            break
                        time.sleep(1)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self._log_security_event(f"Erro no loop de monitoramento: {e}", "ERROR")
                    time.sleep(60)  # Aguardar 1 minuto antes de tentar novamente

        # Iniciar thread de monitoramento
        monitor_thread = threading.Thread(target=monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()

        return monitor_thread

    def stop_monitoring(self):
        """Para o monitoramento"""
        self.running = False
        self._log_security_event("Parando monitoramento contínuo", "INFO")

    def save_report(self, filename: str = None):
        """Salva relatório de segurança em arquivo"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"logs/security_report_{timestamp}.txt"

        try:
            report = self.generate_security_report()

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)

            self._log_security_event(f"Relatório salvo em: {filename}", "INFO")
            return filename

        except Exception as e:
            self._log_security_event(f"Erro ao salvar relatório: {e}", "ERROR")
            return None


def signal_handler(signum, frame):
    """Handler para sinais do sistema"""
    print("\n⏹️ Parando monitoramento de segurança...")
    sys.exit(0)


def main():
    """Função principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Monitor de Segurança FreqTrade3')
    parser.add_argument('--continuous', action='store_true',
                       help='Iniciar monitoramento contínuo')
    parser.add_argument('--scan-once', action='store_true',
                       help='Executar scan único')
    parser.add_argument('--config', type=str, default='configs/security_config.json',
                       help='Arquivo de configuração')
    parser.add_argument('--report', action='store_true',
                       help='Gerar relatório de segurança')
    parser.add_argument('--dashboard', action='store_true',
                       help='Iniciar dashboard web (experimental)')

    args = parser.parse_args()

    # Configurar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Inicializar monitor
    monitor = SecurityMonitor(args.config)

    try:
        if args.continuous:
            print("🔍 Iniciando monitoramento contínuo de segurança...")
            print("Pressione Ctrl+C para parar")
            monitor.start_continuous_monitoring()

            # Manter executando
            while True:
                time.sleep(1)

        elif args.scan_once:
            print("🔍 Executando scan de segurança...")
            results = monitor.run_security_scan()

            print(f"\n📊 RESULTADOS DO SCAN:")
            print(f"   Vulnerabilidades encontradas: {len(results['vulnerabilities'])}")
            print(f"   Duração: {results['scan_duration_seconds']:.2f} segundos")

            for vuln in results['vulnerabilities']:
                severity = vuln.get('severity', 'UNKNOWN')
                print(f"   [{severity}] {vuln.get('description', 'N/A')}")

        elif args.report:
            print("📋 Gerando relatório de segurança...")
            report_file = monitor.save_report()
            if report_file:
                print(f"✅ Relatório salvo em: {report_file}")

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n⏹️ Parando...")
        monitor.stop_monitoring()
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
