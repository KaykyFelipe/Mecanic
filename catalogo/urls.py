from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.ProdutoListView.as_view(), name='estoque-listar'),
    path('login/', auth_views.LoginView.as_view(template_name='catalogo/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('produto/novo/', views.ProdutoCreateView.as_view(), name='estoque-criar'),
    path('produto/<int:pk>/editar/', views.ProdutoUpdateView.as_view(), name='estoque-editar'),
    path('produto/<int:pk>/excluir/', views.ProdutoDeleteView.as_view(), name='estoque-excluir'),
    path('produto/importar-csv/', views.ProdutoImportCSVView.as_view(), name='estoque-importar-csv'),
    path('produto/importar-csv/modelo/', views.download_csv_template, name='estoque-importar-csv-modelo'),
    path('produto/acoes-lote/', views.ProdutoBulkActionView.as_view(), name='estoque-acoes-lote'),
    path('produto/entrada/', views.EntradaEstoqueCreateView.as_view(), name='estoque-entrada'),
    path('produto/entrada/<int:pk>/excluir/', views.EntradaEstoqueDeleteView.as_view(), name='estoque-entrada-excluir'),
    path('produto/etiquetas/', views.ProdutoEtiquetasView.as_view(), name='estoque-imprimir-etiquetas'),
    path('produto/compatibilidade/adicionar/', views.CompatibilidadeAddView.as_view(), name='compatibilidade-adicionar'),
    path('produto/compatibilidade/<int:pk>/remover/', views.CompatibilidadeRemoveView.as_view(), name='compatibilidade-remover'),
    path('produto/compatibilidades/', views.CompatibilidadeListView.as_view(), name='compatibilidade-listar'),
    path('produto/movimentacoes/', views.ProdutoMovimentacoesView.as_view(), name='produto-movimentacoes'),
    path('categorias/', views.CategoriaListView.as_view(), name='categoria-listar'),
    path('categoria/nova/', views.CategoriaCreateView.as_view(), name='categoria-criar'),
    path('categoria/<int:pk>/editar/', views.CategoriaUpdateView.as_view(), name='categoria-editar'),
    path('categoria/<int:pk>/excluir/', views.CategoriaDeleteView.as_view(), name='categoria-excluir'),
    
    # Tabelas de Preço
    path('tabelas-preco/', views.TabelaPrecoListView.as_view(), name='tabelapreco-listar'),
    path('tabelas-preco/nova/', views.TabelaPrecoCreateView.as_view(), name='tabelapreco-criar'),
    path('tabelas-preco/<int:pk>/editar/', views.TabelaPrecoUpdateView.as_view(), name='tabelapreco-editar'),
    path('tabelas-preco/<int:pk>/excluir/', views.TabelaPrecoDeleteView.as_view(), name='tabelapreco-excluir'),
    path('tabelas-preco/<int:pk>/precos/', views.TabelaPrecoPrecosView.as_view(), name='tabelapreco-precos'),
]
