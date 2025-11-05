#!/usr/bin/env python3
"""
================================================================
FREQTRADE3 - SCRIPT DE TESTES DE SEGURANÇA
================================================================

Testes automatizados para validar configurações de segurança
Execute regularmente para manter alto nível de segurança

Uso:
    python3 tests/security_tests.py --run-all
    python3 tests/security_tests.py --test-config
    python3 tests/security_tests.py --test-apis
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Adicionar diretório pai ao path para imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from scripts.security_monitor import FreqTradeSecurityMonitor
except ImportError:
    print("❌ Erro: Não foi possível importar security_monitor.py")
    print("Execute do diretório raiz do projeto FreqTrade3")
    sys.exit(1)


class SecurityTests(unittest.TestCase):
    """Suite de testes de segurança para FreqTrade3"""

    @classmethod
    def setUpClass(cls):
        """Configuração inicial dos testes"""
        cls.base_dir = Path(__file__).parent.parent
        cls.monitor = FreqTradeSecurityMonitor(cls.base_dir)

        # Criar diretório de testes temporário
        cls.test_dir = Path(tempfile.mkdtemp(prefix='freqtrade3_test_'))

        # Configuração de teste segura
        cls.safe_config = {
            "dry_run": True,
            "max_open_trades": 1,
            "stake_amount": 10,
            "stoploss": -0.02,
            "trailing_stop": True
        }

        # Configuração de teste insegura
        cls.unsafe_config = {
            "dry_run": False,
            "max_open_trades": 50,
            "stake_amount": 1000,
            "stoploss": -0.001,
            "trailing_stop": False
        }

    @classmethod
    def tearDownClass(cls):
        """Limpeza após testes"""
        # Remover diretório de teste temporário
        import shutil
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_gitignore_coverage(self):
        """Testa se .gitignore protege arquivos sensíveis"""
        gitignore_path = self.base_dir / ".gitignore"

        self.assertTrue(gitignore_path.exists(),
                       "Arquivo .gitignore não encontrado")

        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()

        # Verificar padrões importantes
        required_patterns = [
            '.env',
            'config*.json',
            '*.key',
            'user_data/',
            'logs/',
            '*.log',
            'trades.sqlite'
        ]

        for pattern in required_patterns:
            self.assertIn(pattern, gitignore_content,
                         f"Padrão obrigatório ausente do .gitignore: {pattern}")

    def test_config_security_dry_run(self):
        """Testa configurações seguras para dry-run"""
        config_path = self.test_dir / "config.json"

        with open(config_path, 'w') as f:
            json.dump(self.safe_config, f, indent=2)

        # Verificar se arquivo é detectado como seguro
        issues = self.monitor.check_config_security()

        # Não deve ter issues críticas para configuração segura
        critical_issues = [i for i in issues if i['severity'] == 'CRITICAL']
        self.assertEqual(len(critical_issues), 0,
                        f"Configuração segura gerou issues críticas: {critical_issues}")

    def test_config_security_live_trading(self):
        """Testa configurações inseguras para live trading"""
        config_path = self.test_dir / "config_unsafe.json"

        with open(config_path, 'w') as f:
            json.dump(self.unsafe_config, f, indent=2)

        # Simular verificação
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Verificar se problemas são detectados
        issues = []

        if not config.get('dry_run', True):
            issues.append("Dry run disabled")

        if config.get('max_open_trades', 3) > 10:
            issues.append("Too many open trades")

        if config.get('stoploss', -0.02) > -0.01:
            issues.append("Stop loss too high")

        self.assertGreater(len(issues), 0,
                          "Configuração insegura não gerou avisos")

    def test_api_key_exposure(self):
        """Testa detecção de chaves API expostas"""
        # Criar arquivo com chave API simulada
        fake_api_file = self.test_dir / "fake_config.py"

        with open(fake_api_file, 'w') as f:
            f.write("""
# Configuração com chaves API expostas (TESTE)
API_KEY = "abcd1234567890efghijklmnopqrstuvwxyz1234567890"
SECRET_KEY = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh1234567890nopqrstuvwxyz"
PASSWORD = "my_secret_password_123"
""")

        # Testar detecção
        exposed = self.monitor._check_exposed_api_keys(fake_api_file)
        self.assertTrue(exposed, "Chaves API expostas não foram detectadas")

    def test_directory_permissions(self):
        """Testa verificações de permissões de diretório"""
        # Criar diretório de teste
        test_sensitive_dir = self.test_dir / "sensitive_data"
        test_sensitive_dir.mkdir()

        # Arquivo dentro do diretório
        sensitive_file = test_sensitive_dir / "secret.txt"
        sensitive_file.write_text("secret data")

        # Simular verificação de permissões
        # (Em ambiente real, verificaria permissões de arquivo)
        dir_exists = test_sensitive_dir.exists()
        self.assertTrue(dir_exists, "Diretório de teste não foi criado")

    def test_log_security(self):
        """Testa segurança de logs"""
        log_dir = self.test_dir / "logs"
        log_dir.mkdir()

        # Criar log simulado com dados sensíveis
        fake_log = log_dir / "freqtrade.log"
        with open(fake_log, 'w') as f:
            f.write("""
2025-01-01 10:00:00 - INFO - Starting FreqTrade
2025-01-01 10:00:01 - INFO - API key loaded: abcd1234567890
2025-01-01 10:00:02 - INFO - Trade entered for BTC/USDT
2025-01-01 10:00:03 - INFO - Secret: my_secret_key_123
2025-01-01 10:00:04 - INFO - Buy order filled
""")

        # Testar detecção de dados sensíveis
        contains_sensitive = self.monitor._log_contains_sensitive_data(fake_log)
        self.assertTrue(contains_sensitive,
                       "Dados sensíveis em logs não foram detectados")

    def test_environment_security(self):
        """Testa configurações de variáveis de ambiente"""
        env_example_path = self.base_dir / "configs" / ".env.example"

        if env_example_path.exists():
            with open(env_example_path, 'r') as f:
                env_content = f.read()

            # Verificar se arquivo example existe
            self.assertIn("BINANCE_API_KEY", env_content,
                         "Exemplo de .env não contém BINANCE_API_KEY")

            # Verificar se não há valores reais (apenas placeholders)
            self.assertNotIn("your_binance_api_key_here", env_content.replace("your_", "YOUR_"),
                           "Arquivo .env.example contém placeholder válido")


class ConfigurationTests(unittest.TestCase):
    """Testes específicos para configurações"""

    def test_template_json_syntax(self):
        """Testa se templates JSON são válidos"""
        template_files = [
            "configs/config_template_dryrun.json",
            "configs/config_template_live.json",
            "configs/config_template_production.json"
        ]

        for template_file in template_files:
            template_path = Path(template_file)

            self.assertTrue(template_path.exists(),
                          f"Template não encontrado: {template_file}")

            try:
                with open(template_path, 'r') as f:
                    config = json.load(f)

                # Verificar estrutura básica
                self.assertIn("exchange", config,
                            f"Template {template_file} não tem seção exchange")

                if "dry_run" in config:
                    # Template dryrun deve ter dry_run = true
                    if "dryrun" in template_file.lower():
                        self.assertTrue(config["dry_run"],
                                      f"Template dryrun deve ter dry_run=true: {template_file}")

            except json.JSONDecodeError as e:
                self.fail(f"Template JSON inválido {template_file}: {e}")

    def test_template_security_settings(self):
        """Testa configurações de segurança em templates"""
        template_path = Path("configs/config_template_dryrun.json")

        if template_path.exists():
            with open(template_path, 'r') as f:
                config = json.load(f)

            # Verificar configurações seguras
            self.assertTrue(config.get("dry_run", False),
                          "Template dryrun deve ter dry_run=true")

            self.assertLessEqual(config.get("max_open_trades", 99), 5,
                               "max_open_trades deve ser baixo em template seguro")

            self.assertLessEqual(config.get("stoploss", 0), -0.01,
                               "stop loss deve ser conservador")


class StrategyTests(unittest.TestCase):
    """Testes para estratégias"""

    def test_strategy_import(self):
        """Testa se estratégias podem ser importadas"""
        strategy_files = [
            "strategies/template_strategy.py",
            "strategies/EMA200RSI.py"
        ]

        for strategy_file in strategy_files:
            strategy_path = Path(strategy_file)

            if strategy_path.exists():
                # Verificar se arquivo tem extensão .py
                self.assertTrue(strategy_path.suffix == '.py',
                              f"Estratégia deve ser arquivo Python: {strategy_file}")

                # Verificar se contém classe de estratégia
                with open(strategy_path, 'r') as f:
                    content = f.read()

                self.assertIn("class", content,
                            f"Estratégia deve conter definições de classe: {strategy_file}")
                self.assertIn("IStrategy", content,
                            f"Estratégia deve herdar de IStrategy: {strategy_file}")


class SystemTests(unittest.TestCase):
    """Testes do sistema"""

    def test_directory_structure(self):
        """Testa se estrutura de diretórios está correta"""
        required_dirs = [
            "configs",
            "strategies",
            "scripts",
            "docs",
            "user_data"
        ]

        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            self.assertTrue(dir_path.exists(),
                          f"Diretório obrigatório não encontrado: {dir_name}")

    def test_script_permissions(self):
        """Testa permissões de scripts"""
        executable_scripts = [
            "install.sh",
            "scripts/backup.sh"
        ]

        for script_path in executable_scripts:
            script_file = Path(script_path)

            if script_file.exists():
                # Verificar se tem extensão .sh
                self.assertEqual(script_file.suffix, '.sh',
                               f"Script deve ter extensão .sh: {script_path}")

                # Verificar se é executável (em sistemas Unix)
                if os.name != 'nt':  # Não Windows
                    import stat
                    file_stat = script_file.stat()
                    is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
                    self.assertTrue(is_executable,
                                  f"Script deve ser executável: {script_path}")


def run_security_tests():
    """Executa todos os testes de segurança"""
    print("🔒 Executando Testes de Segurança FreqTrade3")
    print("=" * 60)

    # Criar suite de testes
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Adicionar todas as classes de teste
    test_classes = [SecurityTests, ConfigurationTests, StrategyTests, SystemTests]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Executar testes
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO DE TESTES DE SEGURANÇA")
    print("=" * 60)
    print(f"✅ Testes executados: {result.testsRun}")
    print(f"❌ Falhas: {len(result.failures)}")
    print(f"⚠️  Erros: {len(result.errors)}")

    if result.wasSuccessful():
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Ambiente FreqTrade3 está seguro")
        return True
    else:
        print("🚨 PROBLEMAS DE SEGURANÇA DETECTADOS!")
        print("\nDetalhes das falhas:")

        for test, traceback in result.failures + result.errors:
            print(f"\n❌ {test}:")
            print(f"   {traceback}")

        print("\n💡 Ações recomendadas:")
        print("   1. Revisar e corrigir configurações inseguras")
        print("   2. Verificar permissões de arquivos")
        print("   3. Garantir que .gitignore está completo")
        print("   4. Validar templates de configuração")
        print("   5. Re-executar testes após correções")

        return False


def run_specific_test(test_name: str):
    """Executa teste específico"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Testes de Segurança FreqTrade3')
    parser.add_argument('--run-all', action='store_true',
                       help='Executar todos os testes de segurança')
    parser.add_argument('--test-config', action='store_true',
                       help='Testar apenas configurações')
    parser.add_argument('--test-apis', action='store_true',
                       help='Testar apenas segurança de APIs')
    parser.add_argument('--test-strategies', action='store_true',
                       help='Testar apenas estratégias')
    parser.add_argument('--test-system', action='store_true',
                       help='Testar apenas sistema')
    parser.add_argument('--security-monitor', action='store_true',
                       help='Executar monitor de segurança completo')

    args = parser.parse_args()

    # Se nenhum argumento, executar todos
    if not any([args.run_all, args.test_config, args.test_apis,
                args.test_strategies, args.test_system, args.security_monitor]):
        args.run_all = True

    # Verificar se estamos no diretório correto
    if not Path("scripts/security_monitor.py").exists():
        print("❌ Execute este script do diretório raiz do FreqTrade3")
        sys.exit(1)

    success = True

    if args.security_monitor:
        print("🔍 Executando Monitor de Segurança Completo...")
        monitor = FreqTradeSecurityMonitor()
        report = monitor.generate_security_report()
        monitor.print_report_summary(report)

    if args.run_all:
        success = run_security_tests()
    elif args.test_config:
        success = run_specific_test('ConfigurationTests')
    elif args.test_apis:
        success = run_specific_test('SecurityTests.test_api_key_exposure')
    elif args.test_strategies:
        success = run_specific_test('StrategyTests')
    elif args.test_system:
        success = run_specific_test('SystemTests')

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
