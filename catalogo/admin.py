from django.contrib import admin
from .models import Produto

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        'sku', 
        'nome', 
        'marca', 
        'ncm', 
        'preco_venda', 
        'quantidade_estoque', 
        'codigo_barras_ean'
    )
    list_filter = ('marca', 'ncm')
    search_fields = ('sku', 'nome', 'marca', 'ncm', 'codigo_barras_ean')
    list_editable = ('preco_venda', 'quantidade_estoque')
    list_per_page = 25
