import os
import unittest
import coverage

cov = coverage.Coverage(source=["app1"])
cov.start()

tests_path = os.path.join(os.path.dirname(__file__), "app1", "tests")

loader = unittest.TestLoader()
tests = loader.discover(start_dir=tests_path, pattern='test_*.py')
runner = unittest.TextTestRunner(verbosity=2)

print("\n=== Ejecutando pruebas unitarias ===\n")
result = runner.run(tests)

cov.stop()
cov.save()

print("\n--- Reporte de cobertura ---\n")
cov.report(show_missing=True)
cov.html_report(directory='coverage_html_report')

print(f"\nPruebas totales: {result.testsRun}, fallidas: {len(result.failures)}, errores: {len(result.errors)}")
