from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from django.contrib.auth.models import User
from .models import Produto, EntradaEstoque, Categoria, CompatibilidadeProduto, MovimentacaoEstoque

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
        
        self.categoria = Categoria.objects.create(nome="Freios")
        
        self.produto = Produto.objects.create(
            sku="MLB-111111111",
            nome="Pastilha de Freio Bosch",
            codigo_barras_ean="7890000000001",
            marca="Bosch",
            ncm="87083019",
            categoria=self.categoria,
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
            'categoria': self.categoria.id,
            'preco_custo': 20.00,
            'preco_venda': 35.50,
            'quantidade_estoque': 20,
            'estoque_minimo': 5,
            'estoque_maximo': 50,
        }
        response = self.client.post(reverse('estoque-criar'), data)
        self.assertEqual(response.status_code, 302) # Redireciona em caso de sucesso
        self.assertTrue(Produto.objects.filter(sku="MLB-222222222").exists())

    def test_create_view_post_missing_categoria(self):
        """Testa se o cadastro de produtos falha e exibe erro quando a categoria não é incluída"""
        data = {
            'sku': "MLB-333333333",
            'nome': "Filtro de Ar Tecfil",
            'codigo_barras_ean': "7890000000003",
            'marca': "Tecfil",
            'ncm': "84212300",
            'preco_custo': 15.00,
            'preco_venda': 25.00,
            'quantidade_estoque': 30
            # Categoria is missing
        }
        response = self.client.post(reverse('estoque-criar'), data)
        self.assertEqual(response.status_code, 200) # Renders again with errors
        form = response.context['form']
        self.assertIn('categoria', form.errors)
        self.assertIn('Este campo é obrigatório.', form.errors['categoria'])
        self.assertFalse(Produto.objects.filter(sku="MLB-333333333").exists())

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
            'categoria': self.categoria.id,
            'preco_custo': 80.00,
            'preco_venda': 135.00,
            'quantidade_estoque': 10,
            'estoque_minimo': 3,
            'estoque_maximo': 100,
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
        self.assertIn('sku;nome;codigo_barras_ean;marca;ncm;preco_custo;preco_venda;quantidade_estoque', content)

    def test_import_csv_success_create(self):
        """Testa a criação de novos produtos via CSV"""
        csv_data = (
            "sku;nome;codigo_barras_ean;marca;ncm;preco_custo;preco_venda;quantidade_estoque\n"
            "MLB-333333333;Amortecedor Monroe;7890000000003;Monroe;87088000;180,00;299,90;15\n"
            "MLB-444444444;Filtro de Ar Tecfil;7890000000004;Tecfil;84212300;15.50;25.50;30"
        )
        csv_file = SimpleUploadedFile("produtos.csv", csv_data.encode('utf-8'), content_type="text/csv")
        
        response = self.client.post(reverse('estoque-importar-csv'), {'arquivo_csv': csv_file})
        self.assertEqual(response.status_code, 302) # Redirect on success
        
        # Check database records
        p1 = Produto.objects.get(sku="MLB-333333333")
        self.assertEqual(p1.nome, "Amortecedor Monroe")
        self.assertEqual(p1.preco_custo, Decimal('180.00'))
        self.assertEqual(p1.preco_venda, Decimal('299.90'))
        self.assertEqual(p1.quantidade_estoque, 15)
        
        p2 = Produto.objects.get(sku="MLB-444444444")
        self.assertEqual(p2.nome, "Filtro de Ar Tecfil")
        self.assertEqual(p2.preco_custo, Decimal('15.50'))
        self.assertEqual(p2.preco_venda, Decimal('25.50'))
        self.assertEqual(p2.quantidade_estoque, 30)

    def test_import_csv_update_existing(self):
        """Testa a atualização de um produto existente via CSV por SKU"""
        csv_data = (
            "sku;nome;codigo_barras_ean;marca;ncm;preco_custo;preco_venda;quantidade_estoque\n"
            "MLB-888888888;Peça Atualizada Nova;7890000000888;Marca Atualizada;87083019;95,00;150,00;20"
        )
        csv_file = SimpleUploadedFile("produtos_update.csv", csv_data.encode('utf-8'), content_type="text/csv")
        
        response = self.client.post(reverse('estoque-importar-csv'), {'arquivo_csv': csv_file})
        self.assertEqual(response.status_code, 302)
        
        # Verify changes in existing product
        self.produto_existente.refresh_from_db()
        self.assertEqual(self.produto_existente.nome, "Peça Atualizada Nova")
        self.assertEqual(self.produto_existente.marca, "Marca Atualizada")
        self.assertEqual(self.produto_existente.preco_custo, Decimal('95.00'))
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


class ProdutoPMPTestCase(TestCase):
    def setUp(self):
        # Create test user and log in
        self.user = User.objects.create_user(username="testuser", password="testpassword123")
        self.client.login(username="testuser", password="testpassword123")

        self.produto = Produto.objects.create(
            sku="MLB-999999999",
            nome="Cabo de Vela Bosch",
            codigo_barras_ean="7890000000999",
            marca="Bosch",
            ncm="85119000",
            preco_custo=110.00,
            preco_venda=180.00,
            quantidade_estoque=1
        )

    def test_pmp_model_calculation(self):
        """Testa o recálculo do Preço Médio Ponderado (PMP) ao salvar EntradaEstoque"""
        # Compra 2 unidades por R$ 60,00 cada
        entrada = EntradaEstoque.objects.create(
            produto=self.produto,
            quantidade=2,
            preco_custo=60.00,
            observacao="Compra do fornecedor AutoMais"
        )
        
        self.produto.refresh_from_db()
        # Quantidade total: 1 + 2 = 3
        self.assertEqual(self.produto.quantidade_estoque, 3)
        # PMP: ((1 * 110) + (2 * 60)) / 3 = 230 / 3 = 76.67
        self.assertAlmostEqual(float(self.produto.preco_custo), 76.67, places=2)

    def test_pmp_view_creation(self):
        """Testa o registro de entrada de estoque via view (POST)"""
        data = {
            'produto': self.produto.id,
            'quantidade': 4,
            'preco_custo': 80.00,
            'observacao': "Nota fiscal NF-889"
        }
        
        response = self.client.post(reverse('estoque-entrada'), data)
        self.assertEqual(response.status_code, 302) # Redirect on success
        
        self.produto.refresh_from_db()
        # Quantidade total: 1 + 4 = 5
        self.assertEqual(self.produto.quantidade_estoque, 5)
        # PMP: ((1 * 110) + (4 * 80)) / 5 = 430 / 5 = 86.00
        self.assertEqual(float(self.produto.preco_custo), 86.00)

    def test_pmp_rollback_on_deletion(self):
        """Testa se a exclusão de uma EntradaEstoque reverte o PMP e o estoque corretamente"""
        # Adiciona entrada
        entrada = EntradaEstoque.objects.create(
            produto=self.produto,
            quantidade=2,
            preco_custo=60.00,
            observacao="Compra teste"
        )
        
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 3)
        self.assertAlmostEqual(float(self.produto.preco_custo), 76.67, places=2)
        
        # Deleta a entrada
        entrada.delete()
        self.produto.refresh_from_db()
        
        # Deve voltar para a quantidade 1 e custo R$ 110.00
        self.assertEqual(self.produto.quantidade_estoque, 1)
        self.assertAlmostEqual(float(self.produto.preco_custo), 110.00, places=1)

    def test_pmp_rollback_view_post(self):
        """Testa se a exclusão de entrada via view (POST) funciona e redireciona com sucesso"""
        entrada = EntradaEstoque.objects.create(
            produto=self.produto,
            quantidade=2,
            preco_custo=60.00,
            observacao="Compra teste"
        )
        
        # POST para a view de exclusão
        response = self.client.post(reverse('estoque-entrada-excluir', args=[entrada.id]))
        self.assertEqual(response.status_code, 302) # Redireciona com sucesso
        self.assertIn(f"produto_id={self.produto.id}", response['Location'])
        
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 1)
        self.assertAlmostEqual(float(self.produto.preco_custo), 110.00, places=1)


class PremiumFeaturesTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword123")
        self.client.login(username="testuser", password="testpassword123")
        
        # 1. Categories setup
        self.cat_pai = Categoria.objects.create(nome="Motor")
        self.cat_filha = Categoria.objects.create(nome="Filtros", parent=self.cat_pai)
        
        # 2. Product setup linked to Category
        self.produto = Produto.objects.create(
            sku="MLB-888999111",
            nome="Filtro de Combustível Injetado",
            codigo_barras_ean="7890000000889",
            marca="Fram",
            ncm="84212300",
            categoria=self.cat_filha,
            preco_custo=20.00,
            preco_venda=35.00,
            quantidade_estoque=10
        )

    def test_categoria_tree_and_str(self):
        """Testa se a Categoria mantém a hierarquia e gera __str__ correto"""
        self.assertEqual(self.cat_pai.nome, "Motor")
        self.assertEqual(self.cat_filha.parent, self.cat_pai)
        self.assertEqual(str(self.cat_pai), "Motor")
        self.assertEqual(str(self.cat_filha), "Motor > Filtros")

    def test_produto_linked_to_categoria(self):
        """Testa se o produto carrega a categoria corretamente e pode ser filtrado"""
        self.assertEqual(self.produto.categoria, self.cat_filha)
        
        # Test filter view
        response = self.client.get(reverse('estoque-listar'), {'categoria': self.cat_filha.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Filtro de Combustível Injetado")

    def test_kardex_auto_logging(self):
        """Testa a geração automática de logs no Kardex (MovimentacaoEstoque)"""
        # 1. Product creation Kardex log check
        # (setUp already created self.produto with quantity 10)
        movs = MovimentacaoEstoque.objects.filter(produto=self.produto)
        self.assertEqual(movs.count(), 1)
        self.assertEqual(movs.first().tipo, 'A') # Ajuste/Saldo Inicial
        self.assertEqual(movs.first().saldo_atual, 10)
        
        # 2. Product manual edit stock change
        self.produto.quantidade_estoque = 15
        self.produto.save()
        
        movs_updated = MovimentacaoEstoque.objects.filter(produto=self.produto).order_by('-data')
        self.assertEqual(movs_updated.count(), 2)
        # Latest should be Entrada/Ajuste of diff=5
        latest = movs_updated.first()
        self.assertEqual(latest.tipo, 'E')
        self.assertEqual(latest.quantidade, 5)
        self.assertEqual(latest.saldo_anterior, 10)
        self.assertEqual(latest.saldo_atual, 15)

    def test_compatibilidade_ajax_endpoints(self):
        """Testa AJAX de compatibilidade (adicionar, listar, remover)"""
        # 1. AJAX Add Compatibility
        data = {
            'produto_id': self.produto.id,
            'marca_carro': 'Fiat',
            'modelo_carro': 'Uno',
            'ano_carro': '2012'
        }
        res_add = self.client.post(reverse('compatibilidade-adicionar'), data)
        self.assertEqual(res_add.status_code, 200)
        json_add = res_add.json()
        self.assertTrue(json_add['success'])
        self.assertEqual(json_add['marca'], 'Fiat')
        self.assertEqual(json_add['modelo'], 'Uno')
        compat_id = json_add['id']
        
        # Check database
        self.assertTrue(CompatibilidadeProduto.objects.filter(id=compat_id).exists())
        
        # 2. AJAX List Compatibility
        res_list = self.client.get(reverse('compatibilidade-listar'), {'produto_id': self.produto.id})
        self.assertEqual(res_list.status_code, 200)
        json_list = res_list.json()
        self.assertTrue(json_list['success'])
        self.assertEqual(len(json_list['compatibilidades']), 1)
        self.assertEqual(json_list['compatibilidades'][0]['modelo'], 'Uno')
        
        # 3. AJAX Remove Compatibility
        res_remove = self.client.post(reverse('compatibilidade-remover', args=[compat_id]))
        self.assertEqual(res_remove.status_code, 200)
        json_remove = res_remove.json()
        self.assertTrue(json_remove['success'])
        self.assertFalse(CompatibilidadeProduto.objects.filter(id=compat_id).exists())

    def test_produto_etiquetas_printing_view(self):
        """Testa a view de impressão de etiquetas em lote"""
        # POST selection
        response = self.client.post(reverse('estoque-imprimir-etiquetas'), {
            'selected_products': [self.produto.id]
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalogo/etiquetas_print.html')
        self.assertContains(response, "Filtro de Combustível Injetado")
        self.assertContains(response, "MLB-888999111")

    def test_categoria_crud_views(self):
        """Testa o conjunto completo de telas e views de CRUD de Categorias"""
        # 1. Test Categoria List View (GET)
        res_list = self.client.get(reverse('categoria-listar'))
        self.assertEqual(res_list.status_code, 200)
        self.assertTemplateUsed(res_list, 'catalogo/categoria_list.html')
        self.assertContains(res_list, "Motor")
        self.assertContains(res_list, "Filtros")

        # 2. Test Categoria Create View (GET & POST)
        res_create_get = self.client.get(reverse('categoria-criar'))
        self.assertEqual(res_create_get.status_code, 200)
        self.assertTemplateUsed(res_create_get, 'catalogo/categoria_form.html')

        create_data = {
            'nome': 'Suspensão a Ar',
            'parent': self.cat_pai.id # links to parent 'Motor'
        }
        res_create_post = self.client.post(reverse('categoria-criar'), create_data)
        self.assertEqual(res_create_post.status_code, 302) # Redirects on success
        self.assertTrue(Categoria.objects.filter(nome='Suspensão a Ar', parent=self.cat_pai).exists())
        new_cat = Categoria.objects.get(nome='Suspensão a Ar')

        # 3. Test Categoria Update View (GET & POST)
        res_update_get = self.client.get(reverse('categoria-editar', args=[new_cat.id]))
        self.assertEqual(res_update_get.status_code, 200)
        self.assertTemplateUsed(res_update_get, 'catalogo/categoria_form.html')

        update_data = {
            'nome': 'Suspensão Pneumática',
            'parent': '' # moves to principal
        }
        res_update_post = self.client.post(reverse('categoria-editar', args=[new_cat.id]), update_data)
        self.assertEqual(res_update_post.status_code, 302)
        new_cat.refresh_from_db()
        self.assertEqual(new_cat.nome, 'Suspensão Pneumática')
        self.assertIsNone(new_cat.parent)

        # 4. Test Categoria Delete View (GET & POST)
        # Deleting 'self.cat_pai' should cascade delete 'self.cat_filha'
        res_delete_get = self.client.get(reverse('categoria-excluir', args=[self.cat_pai.id]))
        self.assertEqual(res_delete_get.status_code, 200)
        self.assertTemplateUsed(res_delete_get, 'catalogo/categoria_confirm_delete.html')

        res_delete_post = self.client.post(reverse('categoria-excluir', args=[self.cat_pai.id]))
        self.assertEqual(res_delete_post.status_code, 302)
        self.assertFalse(Categoria.objects.filter(id=self.cat_pai.id).exists())
        self.assertFalse(Categoria.objects.filter(id=self.cat_filha.id).exists()) # Cascaded delete!

    def test_fipe_vehicle_filter_view(self):
        """Testa o filtro por veículos compatíveis FIPE na visualização de listagem"""
        # Create a compatibility
        CompatibilidadeProduto.objects.create(
            produto=self.produto,
            marca_carro="Chevrolet",
            modelo_carro="Celta",
            ano_carro="2010 Gasolina"
        )
        
        # 1. Filter by Marca -> Chevrolet (Should display product)
        response_marca = self.client.get(reverse('estoque-listar'), {'compat_marca': 'Chevrolet'})
        self.assertEqual(response_marca.status_code, 200)
        self.assertContains(response_marca, "Filtro de Combustível Injetado")
        
        # 2. Filter by Model -> Celta (Should display product)
        response_model = self.client.get(reverse('estoque-listar'), {'compat_marca': 'Chevrolet', 'compat_modelo': 'Celta'})
        self.assertEqual(response_model.status_code, 200)
        self.assertContains(response_model, "Filtro de Combustível Injetado")

        # 3. Filter by Year -> 2010 Gasolina (Should display product)
        response_year = self.client.get(reverse('estoque-listar'), {
            'compat_marca': 'Chevrolet', 
            'compat_modelo': 'Celta', 
            'compat_ano': '2010 Gasolina'
        })
        self.assertEqual(response_year.status_code, 200)
        self.assertContains(response_year, "Filtro de Combustível Injetado")
        
        # 4. Filter by wrong brand -> Fiat (Should NOT display product)
        response_wrong = self.client.get(reverse('estoque-listar'), {'compat_marca': 'Fiat'})
        self.assertEqual(response_wrong.status_code, 200)
        self.assertNotContains(response_wrong, "Filtro de Combustível Injetado")


class EstoqueMinMaxTestCase(TestCase):
    """Testa a funcionalidade de estoque mínimo e máximo configurável por produto"""
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword123")
        self.client.login(username="testuser", password="testpassword123")
        self.categoria = Categoria.objects.create(nome="Freios")

    def test_estoque_minimo_default_value(self):
        """Testa se o valor padrão de estoque mínimo é 5"""
        produto = Produto.objects.create(
            sku="MIN-001", nome="Pastilha Freio", marca="Bosch",
            ncm="87083019", preco_venda=100.00, quantidade_estoque=10
        )
        self.assertEqual(produto.estoque_minimo, 5)
        self.assertEqual(produto.estoque_maximo, 0)

    def test_estoque_minimo_custom_value(self):
        """Testa se é possível definir um valor personalizado de estoque mínimo"""
        produto = Produto.objects.create(
            sku="MIN-002", nome="Disco Freio", marca="Fremax",
            ncm="87083019", preco_venda=200.00, quantidade_estoque=3,
            estoque_minimo=10, estoque_maximo=50
        )
        self.assertEqual(produto.estoque_minimo, 10)
        self.assertEqual(produto.estoque_maximo, 50)

    def test_kpi_uses_dynamic_minimo(self):
        """Testa se o KPI 'Estoque Baixo' usa o estoque_minimo do produto"""
        # Produto com estoque 8 e mínimo 10 -> deve ser "baixo"
        Produto.objects.create(
            sku="MIN-003", nome="Correia Dentada", marca="Gates",
            ncm="40103900", preco_venda=80.00,
            quantidade_estoque=8, estoque_minimo=10
        )
        # Produto com estoque 8 e mínimo 5 -> deve ser "ok"
        Produto.objects.create(
            sku="MIN-004", nome="Tensor Correia", marca="INA",
            ncm="84839000", preco_venda=120.00,
            quantidade_estoque=8, estoque_minimo=5
        )
        response = self.client.get(reverse('estoque-listar'))
        self.assertEqual(response.status_code, 200)
        # Should count 1 as low stock (MIN-003)
        self.assertEqual(response.context['estoque_baixo'], 1)

    def test_status_filter_ok_uses_minimo(self):
        """Testa se o filtro 'ok' retorna apenas produtos acima do mínimo"""
        p_ok = Produto.objects.create(
            sku="MIN-005", nome="Bomba Dagua", marca="Urba",
            ncm="84135019", preco_venda=150.00,
            quantidade_estoque=20, estoque_minimo=10
        )
        p_low = Produto.objects.create(
            sku="MIN-006", nome="Junta Motor", marca="Sabó",
            ncm="84849000", preco_venda=90.00,
            quantidade_estoque=3, estoque_minimo=10
        )
        response = self.client.get(reverse('estoque-listar'), {'status': 'ok'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bomba Dagua")
        self.assertNotContains(response, "Junta Motor")

    def test_status_filter_low_uses_minimo(self):
        """Testa se o filtro 'low' retorna produtos abaixo ou igual ao mínimo"""
        Produto.objects.create(
            sku="MIN-007", nome="Vela Ignição", marca="NGK",
            ncm="85111000", preco_venda=30.00,
            quantidade_estoque=5, estoque_minimo=5
        )
        response = self.client.get(reverse('estoque-listar'), {'status': 'low'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vela Ignição")

    def test_form_includes_minimo_maximo(self):
        """Testa se o formulário de produto inclui os campos de estoque mínimo e máximo"""
        response = self.client.get(reverse('estoque-criar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id_estoque_minimo')
        self.assertContains(response, 'id_estoque_maximo')

    def test_create_with_custom_minmax(self):
        """Testa criação de produto com valores personalizados de mín/máx"""
        data = {
            'sku': 'MIN-008', 'nome': 'Rolamento Roda', 'marca': 'SKF',
            'ncm': '84822000', 'preco_custo': 40.00, 'preco_venda': 75.00,
            'quantidade_estoque': 12, 'estoque_minimo': 8, 'estoque_maximo': 30,
            'categoria': self.categoria.id,
        }
        response = self.client.post(reverse('estoque-criar'), data)
        self.assertEqual(response.status_code, 302)
        produto = Produto.objects.get(sku='MIN-008')
        self.assertEqual(produto.estoque_minimo, 8)
        self.assertEqual(produto.estoque_maximo, 30)
