from django import forms
from .models import Produto

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            'sku', 
            'nome', 
            'codigo_barras_ean', 
            'marca', 
            'ncm', 
            'preco_venda', 
            'quantidade_estoque'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: MLB-123456789'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Par de Amortecedores Dianteiros'
            }),
            'codigo_barras_ean': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: 7891234567890'
            }),
            'marca': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Cofap'
            }),
            'ncm': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: 87088000'
            }),
            'preco_venda': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'quantidade_estoque': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '0'
            }),
        }

class ProdutoCSVImportForm(forms.Form):
    arquivo_csv = forms.FileField(
        label="Selecione o arquivo CSV",
        help_text="O arquivo deve estar no formato CSV (delimitado por vírgula ou ponto-e-vírgula).",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

