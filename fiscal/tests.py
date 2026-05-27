from django.test import TestCase
from .models import MatrizTributaria

class MatrizTributariaModelTestCase(TestCase):
    def setUp(self):
        self.matriz = MatrizTributaria.objects.create(
            uf_origem="SP",
            uf_destino="RJ",
            ncm="87088000",
            cfop="6102",
            csosn="0102",
            cst="000"
        )

    def test_matriz_creation(self):
        """Testa se a matriz tributária é criada corretamente no banco de dados"""
        self.assertEqual(self.matriz.uf_origem, "SP")
        self.assertEqual(self.matriz.uf_destino, "RJ")
        self.assertEqual(self.matriz.ncm, "87088000")
        self.assertEqual(self.matriz.cfop, "6102")
        self.assertEqual(self.matriz.csosn, "0102")
        self.assertEqual(self.matriz.cst, "000")

    def test_matriz_str_representation(self):
        """Testa a representação em string (__str__) do model"""
        expected_str = "SP -> RJ | NCM: 87088000 | CFOP: 6102"
        self.assertEqual(str(self.matriz), expected_str)

    def test_matriz_empty_ncm_representation(self):
        """Testa a representação em string quando o NCM está vazio"""
        matriz_sem_ncm = MatrizTributaria.objects.create(
            uf_origem="SP",
            uf_destino="MG",
            ncm="",
            cfop="5102",
            cst="101"
        )
        expected_str = "SP -> MG | NCM: Todos NCMs | CFOP: 5102"
        self.assertEqual(str(matriz_sem_ncm), expected_str)
