from django.db import models

class MatrizTributaria(models.Model):
    uf_origem = models.CharField(
        max_length=2,
        default='SP',
        verbose_name="UF Origem",
        help_text="Identifica o estado de saída da mercadoria."
    )
    uf_destino = models.CharField(
        max_length=2,
        verbose_name="UF Destino",
        help_text="Identifica o estado do comprador."
    )
    ncm = models.CharField(
        max_length=8,
        blank=True,
        verbose_name="NCM",
        help_text="Define qual NCM a regra afeta."
    )
    cfop = models.CharField(
        max_length=4,
        verbose_name="CFOP",
        help_text="Código Fiscal de Operações a ser aplicado."
    )
    csosn = models.CharField(
        max_length=4,
        blank=True,
        verbose_name="CSOSN",
        help_text="Código de situação tributária (se Simples Nacional)."
    )
    cst = models.CharField(
        max_length=3,
        blank=True,
        verbose_name="CST",
        help_text="Código de situação tributária (se Lucro Real/Presumido)."
    )

    class Meta:
        verbose_name = "Matriz Tributária"
        verbose_name_plural = "Matrizes Tributárias"
        ordering = ["uf_origem", "uf_destino", "ncm"]

    def __str__(self):
        ncm_display = self.ncm if self.ncm else "Todos NCMs"
        return f"{self.uf_origem} -> {self.uf_destino} | NCM: {ncm_display} | CFOP: {self.cfop}"
