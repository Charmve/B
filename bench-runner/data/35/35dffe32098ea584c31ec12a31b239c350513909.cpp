#include <benchmark/benchmark.h>
static void StringCreation(benchmark::State& state) {
  // Code inside this loop is measured repeatedly
  for (auto _ : state) {
    std::string created_string("hello");
    // Make sure the variable is not optimized away by compiler
    benchmark::DoNotOptimize(created_string);
  }
}
// Register the function as a benchmark
BENCHMARK(StringCreation);

static void StringCopy(benchmark::State& state) {
  // Code before the loop is not measured
  std::string x = "hello";
  for (auto _ : state) {
    std::string copy(x);
  }
}
BENCHMARK(StringCopy);


static void Noop(benchmark::State& state) {
  for (auto _ : state) benchmark::DoNotOptimize(0);
}
BENCHMARK(Noop);
BENCHMARK_MAIN();