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
]
