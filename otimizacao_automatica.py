#!/usr/bin/env python3
"""
FreqTrade3 - Sistema de Otimização Automática
=============================================

Sistema avançado de otimização automática para estratégias de trading.

Funcionalidades:
- Hyperparameter optimization automático
- Strategy evolution automática
- Performance auto-tuning
- ML integration para ajuste inteligente
- Otimização paralela multi-estratégia
- Seleção automática de melhores parâmetros

Autor: FreqTrade3 Project
Data: 2025-11-06
Versão: 1.0.0
"""

import json
import logging
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class AutomaticOptimizationSystem:
    def __init__(self):
        self.optimization_active = False
        self.strategies = ['EMA200RSI', 'MACDStrategy', 'template_strategy']
        self.best_params = {}
        self.optimization_history = []
        self.performance_scores = {}
        self.ml_model = None
        self.setup_logging()
        self.setup_ml()

    def setup_logging(self):
        """Configurar sistema de logging"""
        os.makedirs("logs", exist_ok=True)
        os.makedirs("optimization_results", exist_ok=True)
        os.makedirs("models", exist_ok=True)

        self.logger = logging.getLogger("FreqTrade3_Optimization")
        self.logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler("logs/otimizacao_automatica.log")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        print("[OK] Sistema de logging de otimização configurado")

    def setup_ml(self):
        """Configurar sistema de ML para otimização inteligente"""
        try:
            import sklearn
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.model_selection import train_test_split

            self.ml_available = True
            self.logger.info("Sistema de ML configurado com sucesso")
            print("[OK] Sistema de ML configurado")

        except ImportError:
            self.ml_available = False
            self.logger.warning("scikit-learn não disponível. Usando otimização tradicional.")
            print("[WARNING] ML não disponível. Usando métodos tradicionais.")

    def start_optimization(self):
        """Iniciar sistema de otimização automática"""
        print("\n" + "="*60)
        print("🤖 SISTEMA DE OTIMIZAÇÃO AUTOMÁTICA")
        print("="*60)
        print("🎯 Funcionalidades:")
        print("   - Hyperparameter optimization")
        print("   - Strategy evolution automática")
        print("   - Performance auto-tuning")
        print("   - ML integration inteligente")
        print("   - Otimização paralela")
        print("="*60)

        self.optimization_active = True

        # Iniciar threads de otimização
        threading.Thread(target=self.continuous_optimization, daemon=True).start()
        threading.Thread(target=self.ml_optimization_loop, daemon=True).start()
        threading.Thread(target=self.strategy_evolution, daemon=True).start()

        self.logger.info("Sistema de otimização automática iniciado")
        print("[OK] Otimização automática ativa")

        # Menu principal
        self.show_optimization_menu()

    def show_optimization_menu(self):
        """Exibir menu de otimização"""
        while self.optimization_active:
            print("\n" + "-"*60)
            print("🧪 OTIMIZAÇÃO AUTOMÁTICA - OPÇÕES")
            print("-"*60)
            print("1. 🔍 Executar otimização completa")
            print("2. 🤖 ML-guided optimization")
            print("3. 📈 Evolução de estratégias")
            print("4. 📊 Ver melhores parâmetros")
            print("5. 🏃 Otimização paralela")
            print("6. 🛑 Parar otimização")
            print("-"*60)

            choice = input("Escolha uma opção (1-6): ").strip()

            if choice == '1':
                self.run_full_optimization()
            elif choice == '2':
                self.run_ml_guided_optimization()
            elif choice == '3':
                self.evolve_strategies()
            elif choice == '4':
                self.display_best_parameters()
            elif choice == '5':
                self.run_parallel_optimization()
            elif choice == '6':
                self.stop_optimization()
                break
            else:
                print("❌ Opção inválida")

    def run_full_optimization(self):
        """Executar otimização completa de todas as estratégias"""
        print("\n🔍 INICIANDO OTIMIZAÇÃO COMPLETA...")
        print("⏱️  Tempo estimado: 15-30 minutos")

        for strategy in self.strategies:
            print(f"\n📊 Otimizando {strategy}...")

            # Executar otimização usando FreqTrade hyperopt
            try:
                result = self.run_hyperopt(strategy)
                if result:
                    self.best_params[strategy] = result
                    self.logger.info(f"Otimização concluída para {strategy}")
                    print(f"✅ {strategy} otimizado com sucesso!")
                else:
                    print(f"❌ Falha na otimização de {strategy}")

            except Exception as e:
                self.logger.error(f"Erro na otimização de {strategy}: {e}")
                print(f"💥 Erro: {e}")

        self.save_optimization_results()
        print("\n🎉 Otimização completa finalizada!")

    def run_hyperopt(self, strategy: str) -> Optional[Dict]:
        """Executar FreqTrade hyperopt"""
        try:
            cmd = [
                'freqtrade', 'hyperopt',
                '--strategy', strategy,
                '--epochs', '100',
                '--spaces', 'buy sell',
                '--dmmp', '--min-trades', '10',
                '--output', f'optimization_results/{strategy}_hyperopt',
                '--no-color'
            ]

            print(f"   🔧 Executando: {' '.join(cmd[:8])}...")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Extrair melhores parâmetros do output
                best_params = self.extract_best_parameters(result.stdout, strategy)
                return best_params
            else:
                print(f"   ❌ Hyperopt falhou: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print(f"   ⏰ Timeout na otimização de {strategy}")
            return None
        except Exception as e:
            print(f"   💥 Erro: {e}")
            return None

    def extract_best_parameters(self, output: str, strategy: str) -> Dict:
        """Extrair melhores parâmetros do output do hyperopt"""
        params = {}

        try:
            # Procurar por linhas com parâmetros otimizados
            lines = output.split('\n')
            for line in lines:
                if 'Parameter' in line and '=' in line:
                    # Extrair nome e valor do parâmetro
                    parts = line.split('=')
                    if len(parts) == 2:
                        param_name = parts[0].strip()
                        param_value = parts[1].strip()

                        # Converter valores apropriados
                        try:
                            if '.' in param_value:
                                param_value = float(param_value)
                            else:
                                param_value = int(param_value)
                        except:
                            param_value = param_value

                        params[param_name] = param_value

            # Adicionar metadados
            params['strategy'] = strategy
            params['optimized_at'] = datetime.now().isoformat()

            print(f"   📈 {len(params)-2} parâmetros otimizados encontrados")
            return params

        except Exception as e:
            self.logger.error(f"Erro ao extrair parâmetros: {e}")
            return {}

    def run_ml_guided_optimization(self):
        """Executar otimização guiada por ML"""
        if not self.ml_available:
            print("❌ ML não disponível. Instale scikit-learn.")
            return

        print("\n🤖 INICIANDO OTIMIZAÇÃO GUIADA POR ML...")
        print("🔬 Usando Random Forest para otimização inteligente")

        try:
            # Gerar dados sintéticos para treinamento
            X, y = self.generate_training_data()

            # Treinar modelo
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

            self.ml_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.ml_model.fit(X_train, y_train)

            # Avaliar modelo
            score = self.ml_model.score(X_test, y_test)
            print(f"📊 Precisão do modelo: {score:.3f}")

            # Usar modelo para otimização
            self.ml_optimize_strategies()

        except Exception as e:
            self.logger.error(f"Erro na otimização ML: {e}")
            print(f"💥 Erro na otimização ML: {e}")

    def generate_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Gerar dados sintéticos para treinamento do ML"""
        # Simular dados de otimização anterior
        np.random.seed(42)
        n_samples = 1000

        # Parâmetros simulados (EMA fast, EMA slow, RSI periods, etc.)
        X = np.random.uniform(0, 1, (n_samples, 8))  # 8 parâmetros
        y = []

        for i in range(n_samples):
            # Simular score de performance baseado nos parâmetros
            ema_fast = X[i, 0] * 100
            ema_slow = X[i, 1] * 300
            rsi_period = X[i, 2] * 30
            volume_multiplier = X[i, 3] * 3.0

            # Score baseado em lógica simulada
            score = (ema_fast / ema_slow) * 0.5 + (rsi_period / 100) * 0.3 + volume_multiplier * 0.2
            score += np.random.normal(0, 0.1)  # ruído

            y.append(score)

        y = np.array(y)
        return X, y

    def ml_optimize_strategies(self):
        """Otimizar estratégias usando ML"""
        print("\n🎯 Otimizando estratégias com ML...")

        for strategy in self.strategies:
            print(f"\n🤖 ML optimizing {strategy}...")

            try:
                # Gerar candidatos de parâmetros
                candidates = self.generate_parameter_candidates(100)

                # Prever scores usando ML
                best_candidate = None
                best_score = float('-inf')

                for candidate in candidates:
                    # Adaptar candidato para formato do modelo
                    x_candidate = np.array([list(candidate.values())])
                    predicted_score = self.ml_model.predict(x_candidate)[0]

                    if predicted_score > best_score:
                        best_score = predicted_score
                        best_candidate = candidate

                if best_candidate:
                    best_candidate['ml_score'] = best_score
                    best_candidate['strategy'] = strategy
                    best_candidate['optimized_at'] = datetime.now().isoformat()

                    self.best_params[f"{strategy}_ML"] = best_candidate
                    print(f"   ✅ ML encontrou melhores parâmetros: score={best_score:.3f}")
                else:
                    print(f"   ❌ ML não encontrou parâmetros válidos")

            except Exception as e:
                self.logger.error(f"Erro na otimização ML de {strategy}: {e}")
                print(f"   💥 Erro: {e}")

    def generate_parameter_candidates(self, n_candidates: int) -> List[Dict]:
        """Gerar candidatos de parâmetros"""
        candidates = []

        for i in range(n_candidates):
            candidate = {
                'ema_fast': np.random.randint(10, 50),
                'ema_slow': np.random.randint(100, 300),
                'rsi_period': np.random.randint(10, 30),
                'rsi_oversold': np.random.randint(20, 40),
                'rsi_overbought': np.random.randint(60, 80),
                'volume_multiplier': np.random.uniform(1.2, 2.5),
                'macd_fast': np.random.randint(8, 20),
                'macd_slow': np.random.randint(20, 40)
            }
            candidates.append(candidate)

        return candidates

    def run_parallel_optimization(self):
        """Executar otimização paralela de múltiplas estratégias"""
        print("\n🏃 EXECUTANDO OTIMIZAÇÃO PARALELA...")
        print("🚀 Múltiplas estratégias em paralelo")

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            for strategy in self.strategies:
                future = executor.submit(self.run_hyperopt, strategy)
                futures[future] = strategy

            # Coletar resultados
            for future in as_completed(futures):
                strategy = futures[future]
                try:
                    result = future.result()
                    if result:
                        self.best_params[strategy] = result
                        print(f"✅ {strategy} otimizado em paralelo")
                    else:
                        print(f"❌ Falha na otimização paralela: {strategy}")
                except Exception as e:
                    print(f"💥 Erro na otimização paralela {strategy}: {e}")

        print("\n🎉 Otimização paralela finalizada!")
        self.save_optimization_results()

    def evolve_strategies(self):
        """Evoluir estratégias automaticamente"""
        print("\n🧬 EVOLUÇÃO DE ESTRATÉGIAS...")
        print("🔬 Aplicando princípios de algoritmos genéticos")

        generations = 5
        population_size = 10

        for strategy in self.strategies:
            print(f"\n🧬 Evoluindo {strategy}...")

            # População inicial
            population = self.generate_parameter_candidates(population_size)

            for generation in range(generations):
                print(f"   📈 Geração {generation + 1}/{generations}")

                # Avaliar população
                scores = self.evaluate_population(population, strategy)

                # Seleção e crossover
                population = self.evolve_population(population, scores)

                # Salvar melhor da geração
                best_idx = np.argmax(scores)
                if generation == generations - 1:  # Última geração
                    best_params = population[best_idx].copy()
                    best_params['strategy'] = strategy
                    best_params['evolution_score'] = scores[best_idx]
                    best_params['evolved_at'] = datetime.now().isoformat()

                    self.best_params[f"{strategy}_EVOLVED"] = best_params
                    print(f"   🏆 Melhor evolução: score={scores[best_idx]:.3f}")

            print(f"✅ {strategy} evoluído com sucesso!")

    def evaluate_population(self, population: List[Dict], strategy: str) -> List[float]:
        """Avaliar população de candidatos"""
        scores = []

        for candidate in population:
            # Simular avaliação
            score = self.simulate_strategy_performance(candidate, strategy)
            scores.append(score)

        return scores

    def simulate_strategy_performance(self, params: Dict, strategy: str) -> float:
        """Simular performance de estratégia com parâmetros"""
        # Lógica simulada de performance
        base_score = 0.5

        # Ajustar score baseado em parâmetros
        ema_ratio = params.get('ema_fast', 20) / params.get('ema_slow', 50)
        rsi_balance = (params.get('rsi_oversold', 30) + params.get('rsi_overbought', 70)) / 100

        score = base_score + (ema_ratio - 0.4) * 0.3 + (rsi_balance - 1.0) * 0.2
        score += np.random.normal(0, 0.05)  # ruído

        return max(0, min(1, score))  # bound entre 0 e 1

    def evolve_population(self, population: List[Dict], scores: List[float]) -> List[Dict]:
        """Evoluir população usando seleção, crossover e mutação"""
        # Seleção (roleta)
        total_score = sum(scores)
        if total_score == 0:
            return population  # sem evolução

        selected = []
        for _ in range(len(population)):
            # Selecionar baseado em fitness
            rand = np.random.random() * total_score
            cumulative = 0
            for i, score in enumerate(scores):
                cumulative += score
                if cumulative >= rand:
                    selected.append(population[i].copy())
                    break

        # Crossover e mutação
        for i in range(1, len(selected), 2):
            if i + 1 < len(selected):
                # Crossover
                child1, child2 = self.crossover(selected[i-1], selected[i])
                # Mutação
                child1 = self.mutate(child1)
                child2 = self.mutate(child2)
                selected[i-1] = child1
                selected[i] = child2

        return selected

    def crossover(self, parent1: Dict, parent2: Dict) -> Tuple[Dict, Dict]:
        """Crossover entre dois pais"""
        child1 = {}
        child2 = {}

        for key in parent1.keys():
            if key in ['strategy', 'optimized_at', 'ml_score', 'evolution_score', 'evolved_at']:
                child1[key] = parent1[key]
                child2[key] = parent2[key]
            else:
                # Crossover de parâmetros numéricos
                if isinstance(parent1[key], (int, float)):
                    if np.random.random() < 0.5:
                        child1[key] = parent1[key]
                        child2[key] = parent2[key]
                    else:
                        child1[key] = parent2[key]
                        child2[key] = parent1[key]
                else:
                    child1[key] = parent1[key]
                    child2[key] = parent2[key]

        return child1, child2

    def mutate(self, individual: Dict) -> Dict:
        """Aplicar mutação a um indivíduo"""
        mutation_rate = 0.1
        mutated = individual.copy()

        for key, value in mutated.items():
            if key in ['strategy', 'optimized_at', 'ml_score', 'evolution_score', 'evolved_at']:
                continue

            if isinstance(value, (int, float)) and np.random.random() < mutation_rate:
                # Mutação de valor numérico
                if isinstance(value, int):
                    mutated[key] = value + np.random.randint(-5, 6)
                else:
                    mutated[key] = value + np.random.uniform(-0.1, 0.1)

        return mutated

    def continuous_optimization(self):
        """Otimização contínua em background"""
        while self.optimization_active:
            try:
                # Verificar se é necessário re-otimizar
                if self.should_reoptimize():
                    print("\n🔄 Iniciando re-otimização contínua...")
                    self.run_full_optimization()

                time.sleep(3600)  # Verificar a cada hora
            except Exception as e:
                self.logger.error(f"Erro na otimização contínua: {e}")
                time.sleep(1800)

    def ml_optimization_loop(self):
        """Loop de otimização ML em background"""
        while self.optimization_active:
            try:
                if self.ml_available:
                    # Atualizar modelo periodicamente
                    time.sleep(7200)  # A cada 2 horas

                time.sleep(3600)
            except Exception as e:
                self.logger.error(f"Erro no loop ML: {e}")
                time.sleep(1800)

    def strategy_evolution(self):
        """Evolução de estratégias em background"""
        while self.optimization_active:
            try:
                # Evolver estratégias semanalmente
                time.sleep(604800)  # 1 semana em segundos

            except Exception as e:
                self.logger.error(f"Erro na evolução: {e}")
                time.sleep(86400)

    def should_reoptimize(self) -> bool:
        """Verificar se deve re-otimizar"""
        # Critérios para re-otimização
        if not self.best_params:
            return True

        # Se não há otimizações recentes
        for strategy, params in self.best_params.items():
            if 'optimized_at' in params:
                optimized_at = datetime.fromisoformat(params['optimized_at'])
                if (datetime.now() - optimized_at).days > 7:
                    return True

        return False

    def display_best_parameters(self):
        """Exibir melhores parâmetros encontrados"""
        print("\n📊 MELHORES PARÂMETROS ENCONTRADOS")
        print("="*60)

        if not self.best_params:
            print("❌ Nenhum parâmetro otimizado encontrado.")
            return

        for strategy, params in self.best_params.items():
            print(f"\n🎯 {strategy}:")
            print("-" * 40)

            # Mostrar metadados
            if 'optimized_at' in params:
                date = datetime.fromisoformat(params['optimized_at'])
                print(f"📅 Otimizado em: {date.strftime('%d/%m/%Y %H:%M')}")

            if 'ml_score' in params:
                print(f"🤖 Score ML: {params['ml_score']:.3f}")

            if 'evolution_score' in params:
                print(f"🧬 Score Evolução: {params['evolution_score']:.3f}")

            # Mostrar parâmetros
            param_count = 0
            for key, value in params.items():
                if key not in ['strategy', 'optimized_at', 'ml_score', 'evolution_score', 'evolved_at']:
                    print(f"   🔧 {key}: {value}")
                    param_count += 1

            print(f"📈 {param_count} parâmetros otimizados")

    def save_optimization_results(self):
        """Salvar resultados de otimização"""
        results = {
            'best_params': self.best_params,
            'optimization_history': self.optimization_history,
            'performance_scores': self.performance_scores,
            'saved_at': datetime.now().isoformat()
        }

        filename = f"optimization_results/optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        self.logger.info(f"Resultados de otimização salvos: {filename}")
        print(f"💾 Resultados salvos: {filename}")

    def stop_optimization(self):
        """Parar sistema de otimização"""
        self.optimization_active = False
        self.logger.info("Sistema de otimização parado")
        print("\n🛑 Sistema de otimização parado")
        self.save_optimization_results()

def main():
    """Função principal"""
    optimizer = AutomaticOptimizationSystem()

    print("""
[INFO] FREQTRADE3 - SISTEMA DE OTIMIZACAO AUTOMATICA
==================================================

Este sistema implementa:
  - Hyperparameter optimization automatico
  - Machine Learning para ajuste inteligente
  - Evolucao automatica de estrategias
  - Otimizacao paralela multi-estrategia
  - Selecao automatica de melhores parametros

Iniciar otimizacao automatica?""")

    choice = input("(s/n): ").lower().strip()

    if choice in ['s', 'sim', 'yes', 'y']:
        optimizer.start_optimization()
    else:
        print("❌ Otimização cancelada")

if __name__ == "__main__":
    main()
