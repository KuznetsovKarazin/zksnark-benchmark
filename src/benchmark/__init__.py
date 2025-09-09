"""
Benchmark package for zkSNARK performance testing.
"""

# Version info
__version__ = "1.0.0"

# Core imports
try:
    from .enhanced_runner import (
        EnhancedBenchmarkRunner,
        EnhancedBenchmarkConfig,
        EnhancedBenchmarkResult,
        run_enhanced_benchmark_from_config,
        run_single_circuit_benchmark
    )
    from .enhanced_metrics import (
        DetailedMetrics,
        EnhancedMetricsCollector,
        ScalabilityAnalyzer,
        ScalabilityAnalysis,
        save_enhanced_metrics,
        load_enhanced_metrics
    )
    from .enhanced_visualizer import (
        EnhancedVisualizer,
        create_benchmark_visualizations
    )
    
    ENHANCED_AVAILABLE = True
    
except ImportError as e:
    # Fallback imports for basic functionality
    ENHANCED_AVAILABLE = False
    print(f"Enhanced features not available: {e}")
    
    try:
        from .runner import BenchmarkRunner, BenchmarkConfig
    except ImportError:
        pass

__all__ = [
    "EnhancedBenchmarkRunner",
    "EnhancedBenchmarkConfig", 
    "EnhancedBenchmarkResult",
    "DetailedMetrics",
    "EnhancedMetricsCollector",
    "ScalabilityAnalyzer",
    "EnhancedVisualizer",
    "run_enhanced_benchmark_from_config",
    "run_single_circuit_benchmark",
    "save_enhanced_metrics",
    "load_enhanced_metrics",
    "create_benchmark_visualizations",
    "ENHANCED_AVAILABLE"
]
