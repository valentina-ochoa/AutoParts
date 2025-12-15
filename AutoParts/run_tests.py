import os
import sys
import django
import unittest
import coverage

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AutoParts.settings")
django.setup()

cov = coverage.Coverage(source=["AutoParts"])  
cov.start()

loader = unittest.TestLoader()
suite = loader.discover("AutoParts")  

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

cov.stop()
cov.save()

print("\n\n--- Reporte de cobertura ---")
cov.report(show_missing=True)  
cov.html_report(directory="coverage_html")  

print("\n\n--- Resumen de pruebas ---")
print(f"Total de pruebas: {result.testsRun}")
print(f"Fallidas: {len(result.failures)}")
print(f"Errores: {len(result.errors)}")

if result.failures or result.errors:
    print("\nDetalles de fallas y errores:")
    for test, tb in result.failures + result.errors:
        print(f"\nPrueba que falló: {test}")
        print(tb)
else:
    print("\nTodas las pruebas pasaron correctamente ✅")
