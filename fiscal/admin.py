from django.contrib import admin
from .models import MatrizTributaria

@admin.register(MatrizTributaria)
class MatrizTributariaAdmin(admin.ModelAdmin):
    list_display = (
        'uf_origem', 
        'uf_destino', 
        'ncm', 
        'cfop', 
        'csosn', 
        'cst'
    )
    list_filter = ('uf_origem', 'uf_destino', 'cfop')
    search_fields = ('ncm', 'cfop', 'csosn', 'cst')
    list_editable = ('cfop', 'csosn', 'cst')
    list_per_page = 25
