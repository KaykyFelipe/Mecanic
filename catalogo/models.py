from django.db import models, transaction
from decimal import Decimal

class Categoria(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome da Categoria")
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children', 
        verbose_name="Categoria Pai"
    )

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.nome}"
        return self.nome


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
    preco_custo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Preço de Custo",
        help_text="Valor de aquisição da autopeça."
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
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produtos',
        verbose_name="Categoria"
    )

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]

    @property
    def margem_lucro(self):
        if self.preco_venda and self.preco_venda > 0:
            return float(((self.preco_venda - self.preco_custo) / self.preco_venda) * 100)
        return 0.0

    def __str__(self):
        return f"{self.sku} - {self.nome} ({self.marca})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        skip_kardex = getattr(self, '_skip_kardex', False)
        
        if is_new:
            super().save(*args, **kwargs)
            if not skip_kardex:
                MovimentacaoEstoque.objects.create(
                    produto=self,
                    tipo='A',
                    quantidade=self.quantidade_estoque,
                    saldo_anterior=0,
                    saldo_atual=self.quantidade_estoque,
                    custo_unitario=self.preco_custo,
                    descricao="Saldo Inicial de Cadastro"
                )
        else:
            old_self = Produto.objects.get(pk=self.pk)
            old_qtd = old_self.quantidade_estoque
            super().save(*args, **kwargs)
            
            if not skip_kardex and old_qtd != self.quantidade_estoque:
                diff = self.quantidade_estoque - old_qtd
                tipo = 'E' if diff > 0 else 'S'
                desc = "Ajuste de Saldo Manual (Entrada)" if diff > 0 else "Ajuste de Saldo Manual (Saída)"
                
                MovimentacaoEstoque.objects.create(
                    produto=self,
                    tipo=tipo,
                    quantidade=abs(diff),
                    saldo_anterior=old_qtd,
                    saldo_atual=self.quantidade_estoque,
                    custo_unitario=self.preco_custo,
                    descricao=desc
                )


class EntradaEstoque(models.Model):
    produto = models.ForeignKey(
        Produto, 
        on_delete=models.CASCADE, 
        related_name='entradas', 
        verbose_name="Produto"
    )
    quantidade = models.IntegerField(
        verbose_name="Quantidade Comprada", 
        help_text="Quantidade de itens da nova compra."
    )
    preco_custo = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Preço de Custo Unitário", 
        help_text="Valor unitário pago nesta compra."
    )
    data_entrada = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Data da Entrada"
    )
    observacao = models.TextField(
        blank=True, 
        verbose_name="Observações", 
        help_text="Ex: Nome do Fornecedor, Número da Nota Fiscal, etc."
    )

    class Meta:
        verbose_name = "Entrada de Estoque"
        verbose_name_plural = "Entradas de Estoque"
        ordering = ["-data_entrada"]

    def __str__(self):
        return f"+{self.quantidade} {self.produto.nome} (R$ {self.preco_custo}/un)"

    @property
    def custo_total(self):
        return self.quantidade * self.preco_custo

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        with transaction.atomic():
            super().save(*args, **kwargs)
            
            if is_new:
                # Recalculate PMP (Weighted Average Cost)
                prod = self.produto
                qtd_atual = Decimal(str(prod.quantidade_estoque))
                custo_atual = Decimal(str(prod.preco_custo or '0.00'))
                
                nova_qtd = Decimal(str(self.quantidade))
                novo_custo = Decimal(str(self.preco_custo))
                
                total_itens = qtd_atual + nova_qtd
                
                if total_itens > 0:
                    valor_estoque_atual = qtd_atual * custo_atual
                    valor_nova_compra = nova_qtd * novo_custo
                    novo_custo_medio = (valor_estoque_atual + valor_nova_compra) / total_itens
                else:
                    novo_custo_medio = novo_custo
                
                # Update product details
                prod._skip_kardex = True
                prod.preco_custo = Decimal(str(novo_custo_medio))
                prod.quantidade_estoque = int(total_itens)
                prod.save()
                
                # Create Kardex entry
                MovimentacaoEstoque.objects.create(
                    produto=prod,
                    tipo='E',
                    quantidade=int(nova_qtd),
                    saldo_anterior=int(qtd_atual),
                    saldo_atual=int(total_itens),
                    custo_unitario=Decimal(str(novo_custo)),
                    descricao=f"Compra registrada via Lançamento PMP. Obs: {self.observacao or 'Sem observações'}"
                )

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            prod = self.produto
            qtd_atual = Decimal(str(prod.quantidade_estoque))
            custo_atual = Decimal(str(prod.preco_custo or '0.00'))
            
            qtd_deletada = Decimal(str(self.quantidade))
            custo_deletado = Decimal(str(self.preco_custo))
            
            nova_qtd = qtd_atual - qtd_deletada
            if nova_qtd > 0:
                valor_estoque_atual = qtd_atual * custo_atual
                valor_item_deletado = qtd_deletada * custo_deletado
                novo_valor_estoque = valor_estoque_atual - valor_item_deletado
                
                if novo_valor_estoque < 0:
                    novo_valor_estoque = Decimal('0.00')
                    
                novo_custo_medio = novo_valor_estoque / nova_qtd
            else:
                nova_qtd = Decimal('0.00')
                novo_custo_medio = Decimal('0.00')
                
            # Update product
            prod._skip_kardex = True
            prod.quantidade_estoque = int(nova_qtd)
            prod.preco_custo = Decimal(str(novo_custo_medio))
            prod.save()
            
            # Create Kardex entry
            MovimentacaoEstoque.objects.create(
                produto=prod,
                tipo='S',
                quantidade=int(qtd_deletada),
                saldo_anterior=int(qtd_atual),
                saldo_atual=int(nova_qtd),
                custo_unitario=Decimal(str(custo_deletado)),
                descricao=f"Cancelamento de Entrada PMP. Obs: {self.observacao or 'Sem observações'}"
            )
            
            super().delete(*args, **kwargs)


class CompatibilidadeProduto(models.Model):
    produto = models.ForeignKey(
        Produto, 
        on_delete=models.CASCADE, 
        related_name='compatibilidades', 
        verbose_name="Produto"
    )
    marca_carro = models.CharField(max_length=100, verbose_name="Marca do Carro")
    modelo_carro = models.CharField(max_length=100, verbose_name="Modelo do Carro")
    ano_carro = models.CharField(max_length=50, blank=True, verbose_name="Ano / Versão")

    class Meta:
        verbose_name = "Compatibilidade de Produto"
        verbose_name_plural = "Compatibilidades de Produtos"
        ordering = ["marca_carro", "modelo_carro"]

    def __str__(self):
        return f"{self.produto.nome} ➔ {self.marca_carro} {self.modelo_carro} ({self.ano_carro})"


class MovimentacaoEstoque(models.Model):
    TIPO_CHOICES = [
        ('E', 'Entrada (Compra)'),
        ('S', 'Saída (Venda/Ajuste)'),
        ('A', 'Ajuste Manual'),
    ]
    produto = models.ForeignKey(
        Produto, 
        on_delete=models.CASCADE, 
        related_name='movimentacoes', 
        verbose_name="Produto"
    )
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, verbose_name="Tipo de Movimentação")
    quantidade = models.IntegerField(verbose_name="Quantidade Movimentada")
    saldo_anterior = models.IntegerField(verbose_name="Saldo Anterior")
    saldo_atual = models.IntegerField(verbose_name="Saldo Atual")
    custo_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Custo Unitário"
    )
    data = models.DateTimeField(auto_now_add=True, verbose_name="Data da Movimentação")
    descricao = models.TextField(blank=True, verbose_name="Descrição / Origem")

    class Meta:
        verbose_name = "Movimentação de Estoque"
        verbose_name_plural = "Movimentações de Estoque"
        ordering = ["-data"]

    def __str__(self):
        sinal = "+" if self.tipo == 'E' else "-" if self.tipo == 'S' else ""
        return f"{self.produto.sku} | {self.get_tipo_display()}: {sinal}{self.quantidade} (Saldo: {self.saldo_atual})"
