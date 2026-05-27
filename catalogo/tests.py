from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from django.contrib.auth.models import User
from .models import Produto

class ProdutoModelTestCase(TestCase):
    def setUp(self):
        self.produto = Produto.objects.create(
            sku="MLB-123456789",
            nome="Par de Amortecedores Dianteiros Cofap",
            codigo_barras_ean="7891234567890",
            marca="Cofap",
            ncm="87088000",
            preco_venda=450.00,
            quantidade_estoque=15
        )

    def test_produto_creation(self):
        """Testa se o produto é criado corretamente no banco de dados"""
        self.assertEqual(self.produto.sku, "MLB-123456789")
        self.assertEqual(self.produto.nome, "Par de Amortecedores Dianteiros Cofap")
        self.assertEqual(self.produto.marca, "Cofap")
        self.assertEqual(self.produto.ncm, "87088000")
        self.assertEqual(self.produto.preco_venda, 450.00)
        self.assertEqual(self.produto.quantidade_estoque, 15)

    def test_produto_str_representation(self):
        """Testa a representação em string (__str__) do model"""
        expected_str = "MLB-123456789 - Par de Amortecedores Dianteiros Cofap (Cofap)"
        self.assertEqual(str(self.produto), expected_str)


class ProdutoViewsTestCase(TestCase):
    def setUp(self):
        # Create test user and log in
        self.user = User.objects.create_user(username="testuser", password="testpassword123")
        self.client.login(username="testuser", password="testpassword123")
        
        self.produto = Produto.objects.create(
            sku="MLB-111111111",
            nome="Pastilha de Freio Bosch",
            codigo_barras_ean="7890000000001",
            marca="Bosch",
            ncm="87083019",
            preco_venda=120.00,
            quantidade_estoque=8
        )

    def test_list_view(self):
        """Testa o carregamento correto da página de listagem e seus elementos"""
        response = self.client.get(reverse('estoque-listar'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalogo/produto_list.html')
        self.assertContains(response, "Pastilha de Freio Bosch")
        self.assertContains(response, "MLB-111111111")

    def test_create_view_get(self):
        """Testa a renderização do formulário de cadastro de produtos"""
        response = self.client.get(reverse('estoque-criar'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalogo/produto_form.html')

    def test_create_view_post(self):
        """Testa o envio de dados válidos para cadastrar um produto"""
        data = {
            'sku': "MLB-222222222",
            'nome': "Filtro de Óleo Fram",
            'codigo_barras_ean': "7890000000002",
            'marca': "Fram",
            'ncm': "84212300",
            'preco_venda': 35.50,
            'quantidade_estoque': 20
        }
        response = self.client.post(reverse('estoque-criar'), data)
        self.assertEqual(response.status_code, 302) # Redireciona em caso de sucesso
        self.assertTrue(Produto.objects.filter(sku="MLB-222222222").exists())

    def test_update_view_get(self):
        """Testa a renderização do formulário de edição de produtos"""
        response = self.client.get(reverse('estoque-editar', args=[self.produto.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalogo/produto_form.html')

    def test_update_view_post(self):
        """Testa o envio de edições para atualizar um produto existente"""
        data = {
            'sku': "MLB-111111111",
            'nome': "Pastilha de Freio Bosch Premium",
            'codigo_barras_ean': "7890000000001",
            'marca': "Bosch",
            'ncm': "87083019",
            'preco_venda': 135.00,
            'quantidade_estoque': 10
        }
        response = self.client.post(reverse('estoque-editar', args=[self.produto.id]), data)
        self.assertEqual(response.status_code, 302)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.nome, "Pastilha de Freio Bosch Premium")
        self.assertEqual(self.produto.preco_venda, 135.00)

    def test_delete_view_get(self):
        """Testa a tela de confirmação de exclusão do produto"""
        response = self.client.get(reverse('estoque-excluir', args=[self.produto.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalogo/produto_confirm_delete.html')

    def test_delete_view_post(self):
        """Testa a exclusão definitiva de um produto"""
        response = self.client.post(reverse('estoque-excluir', args=[self.produto.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Produto.objects.filter(id=self.produto.id).exists())


class ProdutoCSVImportTestCase(TestCase):
    def setUp(self):
        # Create test user and log in
        self.user = User.objects.create_user(username="testuser", password="testpassword123")
        self.client.login(username="testuser", password="testpassword123")
        
        self.produto_existente = Produto.objects.create(
            sku="MLB-888888888",
            nome="Peça Antiga",
            codigo_barras_ean="7890000000888",
            marca="Marca Antiga",
            ncm="87083019",
            preco_venda=100.00,
            quantidade_estoque=5
        )

    def test_import_view_get(self):
        """Testa o carregamento da página de importação de CSV"""
        response = self.client.get(reverse('estoque-importar-csv'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalogo/produto_import_csv.html')

    def test_download_template_csv(self):
        """Testa o download do modelo CSV"""
        response = self.client.get(reverse('estoque-importar-csv-modelo'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="modelo_importacao_pecas.csv"', response['Content-Disposition'])
        
        # Verify content has headers
        content = response.content.decode('utf-8')
        self.assertIn('sku;nome;codigo_barras_ean;marca;ncm;preco_venda;quantidade_estoque', content)

    def test_import_csv_success_create(self):
        """Testa a criação de novos produtos via CSV"""
        csv_data = (
            "sku;nome;codigo_barras_ean;marca;ncm;preco_venda;quantidade_estoque\n"
            "MLB-333333333;Amortecedor Monroe;7890000000003;Monroe;87088000;299,90;15\n"
            "MLB-444444444;Filtro de Ar Tecfil;7890000000004;Tecfil;84212300;25.50;30"
        )
        csv_file = SimpleUploadedFile("produtos.csv", csv_data.encode('utf-8'), content_type="text/csv")
        
        response = self.client.post(reverse('estoque-importar-csv'), {'arquivo_csv': csv_file})
        self.assertEqual(response.status_code, 302) # Redirect on success
        
        # Check database records
        p1 = Produto.objects.get(sku="MLB-333333333")
        self.assertEqual(p1.nome, "Amortecedor Monroe")
        self.assertEqual(p1.preco_venda, Decimal('299.90'))
        self.assertEqual(p1.quantidade_estoque, 15)
        
        p2 = Produto.objects.get(sku="MLB-444444444")
        self.assertEqual(p2.nome, "Filtro de Ar Tecfil")
        self.assertEqual(p2.preco_venda, Decimal('25.50'))
        self.assertEqual(p2.quantidade_estoque, 30)

    def test_import_csv_update_existing(self):
        """Testa a atualização de um produto existente via CSV por SKU"""
        csv_data = (
            "sku;nome;codigo_barras_ean;marca;ncm;preco_venda;quantidade_estoque\n"
            "MLB-888888888;Peça Atualizada Nova;7890000000888;Marca Atualizada;87083019;150,00;20"
        )
        csv_file = SimpleUploadedFile("produtos_update.csv", csv_data.encode('utf-8'), content_type="text/csv")
        
        response = self.client.post(reverse('estoque-importar-csv'), {'arquivo_csv': csv_file})
        self.assertEqual(response.status_code, 302)
        
        # Verify changes in existing product
        self.produto_existente.refresh_from_db()
        self.assertEqual(self.produto_existente.nome, "Peça Atualizada Nova")
        self.assertEqual(self.produto_existente.marca, "Marca Atualizada")
        self.assertEqual(self.produto_existente.preco_venda, Decimal('150.00'))
        self.assertEqual(self.produto_existente.quantidade_estoque, 20)

    def test_import_csv_missing_headers(self):
        """Testa o tratamento de erro em arquivo sem colunas obrigatórias"""
        csv_data = (
            "marca;ncm;preco_venda;quantidade_estoque\n"
            "Cofap;87088000;350.00;10"
        )
        csv_file = SimpleUploadedFile("produtos_erro.csv", csv_data.encode('utf-8'), content_type="text/csv")
        
        response = self.client.post(reverse('estoque-importar-csv'), {'arquivo_csv': csv_file})
        self.assertEqual(response.status_code, 200) # Renders the form again
        self.assertTemplateUsed(response, 'catalogo/produto_import_csv.html')
        
        # Ensure no new products were created
        self.assertEqual(Produto.objects.exclude(sku="MLB-888888888").count(), 0)

    def test_import_csv_invalid_values(self):
        """Testa o comportamento do sistema com linhas contendo valores inválidos de preço ou estoque"""
        csv_data = (
            "sku;nome;codigo_barras_ean;marca;ncm;preco_venda;quantidade_estoque\n"
            "MLB-555555555;Filtro Fram;7890000000005;Fram;84212300;preco_invalido;10\n"
            "MLB-666666666;Pastilha Cobreq;7890000000006;Cobreq;87083019;85.00;estoque_invalido"
        )
        csv_file = SimpleUploadedFile("produtos_invalido.csv", csv_data.encode('utf-8'), content_type="text/csv")
        
        response = self.client.post(reverse('estoque-importar-csv'), {'arquivo_csv': csv_file})
        self.assertEqual(response.status_code, 302) # Redirect because parsing proceeds with warnings
        
        # Ensure products with invalid fields were NOT created
        self.assertFalse(Produto.objects.filter(sku="MLB-555555555").exists())
        self.assertFalse(Produto.objects.filter(sku="MLB-666666666").exists())


class ProdutoAuthViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="authuser", password="securepassword123", email="auth@mecanic.com.br")

    def test_anonymous_user_redirected_to_login(self):
        """Testa se um usuário não autenticado é redirecionado do painel para a tela de login"""
        response = self.client.get(reverse('estoque-listar'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_login_view_get(self):
        """Testa se a página de login renderiza com sucesso"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalogo/login.html')

    def test_login_success_post(self):
        """Testa o login bem-sucedido com credenciais válidas"""
        data = {
            'username': 'authuser',
            'password': 'securepassword123'
        }
        response = self.client.post(reverse('login'), data)
        self.assertEqual(response.status_code, 302) # Redireciona para o estoque
        self.assertIn(reverse('estoque-listar'), response['Location'])

    def test_login_failed_post(self):
        """Testa falha de login com credenciais incorretas"""
        data = {
            'username': 'authuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(reverse('login'), data)
        self.assertEqual(response.status_code, 200) # Renders again with errors
        self.assertTemplateUsed(response, 'catalogo/login.html')
        self.assertContains(response, 'Usuário ou senha incorretos')

    def test_logout_post(self):
        """Testa o logout com sucesso desautenticando o usuário"""
        self.client.login(username="authuser", password="securepassword123")
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
