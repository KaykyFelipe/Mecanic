from django.db import models

class Produto(models.Model):
    sku = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="SKU",
        help_text="Código de ligação com o Mercado Livre."
    )
    nome = models.CharField(
        max_length=150, 
        verbose_name="Nome",
        help_text="Descrição da autopeça."
    )
    codigo_barras_ean = models.CharField(
        max_length=14, 
        blank=True, 
        verbose_name="Código de Barras EAN",
        help_text="Requisito forte para exposição no Mercado Livre."
    )
    marca = models.CharField(
        max_length=50, 
        verbose_name="Marca",
        help_text="Evita devoluções por incompatibilidade da peça."
    )
    ncm = models.CharField(
        max_length=8, 
        verbose_name="NCM",
        help_text="Nomenclatura fiscal da peça."
    )
    preco_venda = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Preço de Venda",
        help_text="Valor base para emissão da nota."
    )
    quantidade_estoque = models.IntegerField(
        default=0, 
        verbose_name="Quantidade em Estoque",
        help_text="Saldo atual do item."
    )

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.sku} - {self.nome} ({self.marca})"
