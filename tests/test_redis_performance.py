"""
Тесты производительности Redis для distributed locks
"""

import asyncio
import sys
import time
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / "project"))

from app.utils.locks import redis_lock


@pytest.mark.asyncio
class TestRedisPerformance:
    """Тесты производительности Redis"""

    async def test_lock_throughput(self):
        """
        Тест пропускной способности locks

        Измеряет сколько locks можно получить/освободить в секунду
        """
        iterations = 1000
        start_time = time.time()

        for i in range(iterations):
            async with redis_lock(f"perf:test:{i}", timeout=5, fallback_to_noop=False):
                pass  # Минимальная работа

        elapsed = time.time() - start_time
        throughput = iterations / elapsed

        print("\n📊 Lock Throughput:")
        print(f"  Iterations: {iterations}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.0f} locks/sec")

        # Ожидаем минимум 100 locks/sec
        assert throughput > 100, f"Throughput too low: {throughput:.0f} locks/sec"

    async def test_lock_latency(self):
        """
        Тест задержки получения lock

        Измеряет среднюю задержку получения/освобождения lock
        """
        iterations = 100
        latencies = []

        for i in range(iterations):
            start = time.time()
            async with redis_lock(f"latency:test:{i}", timeout=5, fallback_to_noop=False):
                pass
            latency = (time.time() - start) * 1000  # в миллисекундах
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        p50_latency = sorted(latencies)[len(latencies) // 2]
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        print("\n📊 Lock Latency:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P50: {p50_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  P99: {p99_latency:.2f}ms")

        # Ожидаем среднюю задержку < 10ms
        assert avg_latency < 10, f"Latency too high: {avg_latency:.2f}ms"
        # Ожидаем P99 < 50ms
        assert p99_latency < 50, f"P99 latency too high: {p99_latency:.2f}ms"

    async def test_concurrent_locks(self):
        """
        Тест конкурентных locks

        Измеряет производительность при одновременных запросах
        """
        concurrency = 50
        iterations_per_task = 20

        async def worker(worker_id: int):
            for i in range(iterations_per_task):
                async with redis_lock(f"concurrent:test:{worker_id}:{i}", timeout=5, fallback_to_noop=False):
                    await asyncio.sleep(0.001)  # Минимальная работа

        start_time = time.time()

        # Запускаем workers параллельно
        await asyncio.gather(*[worker(i) for i in range(concurrency)])

        elapsed = time.time() - start_time
        total_operations = concurrency * iterations_per_task
        throughput = total_operations / elapsed

        print("\n📊 Concurrent Locks:")
        print(f"  Concurrency: {concurrency}")
        print(f"  Operations: {total_operations}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.0f} ops/sec")

        # Ожидаем минимум 50 ops/sec при высокой конкуренции
        assert throughput > 50, f"Concurrent throughput too low: {throughput:.0f} ops/sec"

    async def test_lock_contention(self):
        """
        Тест конкуренции за один lock

        Измеряет как быстро locks обрабатываются при конкуренции
        """
        concurrency = 10
        lock_key = "contention:test:shared"

        results = []

        async def worker(worker_id: int):
            start = time.time()
            async with redis_lock(lock_key, timeout=5, blocking_timeout=10, fallback_to_noop=False):
                await asyncio.sleep(0.01)  # Держим lock 10ms
            elapsed = (time.time() - start) * 1000
            results.append({"worker_id": worker_id, "wait_time": elapsed})

        start_time = time.time()

        # Все workers конкурируют за один lock
        await asyncio.gather(*[worker(i) for i in range(concurrency)])

        total_time = time.time() - start_time
        avg_wait = sum(r["wait_time"] for r in results) / len(results)

        print("\n📊 Lock Contention:")
        print(f"  Workers: {concurrency}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg wait: {avg_wait:.2f}ms")
        print(f"  Throughput: {concurrency / total_time:.1f} workers/sec")

        # Проверяем что все workers получили lock
        assert len(results) == concurrency, "Not all workers completed"

        # Ожидаем что среднее время ожидания разумное
        # (должно быть примерно concurrency * hold_time / 2)
        expected_avg = (concurrency * 10) / 2  # 10ms hold time
        assert avg_wait < expected_avg * 2, f"Wait time too high: {avg_wait:.2f}ms"

    async def test_connection_pool_reuse(self):
        """
        Тест переиспользования соединений из pool

        Проверяет что connection pool работает эффективно
        """
        iterations = 100

        start_time = time.time()

        # Быстрые последовательные операции должны переиспользовать соединения
        for i in range(iterations):
            async with redis_lock(f"pool:test:{i}", timeout=5, fallback_to_noop=False):
                pass

        elapsed = time.time() - start_time
        throughput = iterations / elapsed

        print("\n📊 Connection Pool:")
        print(f"  Iterations: {iterations}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.0f} ops/sec")

        # С connection pool должно быть быстрее чем без него
        # Ожидаем минимум 200 ops/sec (с pool)
        assert throughput > 200, f"Pool throughput too low: {throughput:.0f} ops/sec"


@pytest.mark.asyncio
class TestRedisStress:
    """Стресс-тесты Redis"""

    @pytest.mark.slow
    async def test_sustained_load(self):
        """
        Тест устойчивой нагрузки

        Проверяет стабильность при длительной нагрузке
        """
        duration = 60  # 1 минута
        concurrency = 20

        stop_event = asyncio.Event()
        counters = {"success": 0, "errors": 0}

        async def worker(worker_id: int):
            while not stop_event.is_set():
                try:
                    async with redis_lock(f"stress:test:{worker_id}", timeout=5, fallback_to_noop=False):
                        await asyncio.sleep(0.01)
                    counters["success"] += 1
                except Exception as e:
                    counters["errors"] += 1
                    print(f"Worker {worker_id} error: {e}")

        # Запускаем workers
        workers = [asyncio.create_task(worker(i)) for i in range(concurrency)]

        # Ждем duration секунд
        await asyncio.sleep(duration)

        # Останавливаем workers
        stop_event.set()
        await asyncio.gather(*workers, return_exceptions=True)

        total_ops = counters["success"] + counters["errors"]
        throughput = total_ops / duration
        error_rate = counters["errors"] / total_ops if total_ops > 0 else 0

        print(f"\n📊 Sustained Load ({duration}s):")
        print(f"  Concurrency: {concurrency}")
        print(f"  Total ops: {total_ops}")
        print(f"  Success: {counters['success']}")
        print(f"  Errors: {counters['errors']}")
        print(f"  Throughput: {throughput:.0f} ops/sec")
        print(f"  Error rate: {error_rate * 100:.2f}%")

        # Ожидаем минимум 100 ops/sec
        assert throughput > 100, f"Sustained throughput too low: {throughput:.0f} ops/sec"
        # Ожидаем error rate < 1%
        assert error_rate < 0.01, f"Error rate too high: {error_rate * 100:.2f}%"


if __name__ == "__main__":
    # Запуск тестов производительности
    pytest.main([__file__, "-v", "-s", "--tb=short"])
