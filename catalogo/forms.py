from django import forms
from .models import Produto, EntradaEstoque, Categoria

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            'sku', 
            'nome', 
            'codigo_barras_ean', 
            'marca', 
            'ncm', 
            'categoria',
            'preco_custo',
            'preco_venda', 
            'quantidade_estoque'
        ]
        widgets = {
            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),
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
            'preco_custo': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '0.00',
                'step': '0.01'
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].empty_label = "Selecione uma Categoria (Obrigatório)"
        self.fields['categoria'].required = True

class ProdutoCSVImportForm(forms.Form):
    arquivo_csv = forms.FileField(
        label="Selecione o arquivo CSV",
        help_text="O arquivo deve estar no formato CSV (delimitado por vírgula ou ponto-e-vírgula).",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )


class EntradaEstoqueForm(forms.ModelForm):
    class Meta:
        model = EntradaEstoque
        fields = ['produto', 'quantidade', 'preco_custo', 'observacao']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 10', 'min': '1'}),
            'preco_custo': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 45.90', 'step': '0.01'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: Nota Fiscal nº 4580, Fornecedor AutoMais'}),
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'parent']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: Suspensão, Filtros de Óleo'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].empty_label = "Nenhuma (Esta será uma Categoria Principal)"
        self.fields['parent'].label = "Categoria Pai"
        
        # Prevent selecting itself as its parent (prevents database recursive deadlock)
        if self.instance and self.instance.pk:
            self.fields['parent'].queryset = Categoria.objects.exclude(pk=self.instance.pk)

