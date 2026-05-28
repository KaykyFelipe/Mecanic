from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views import View
from django.urls import reverse_lazy
from django.db.models import F, Sum, Q
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import Produto, EntradaEstoque, Categoria, CompatibilidadeProduto, MovimentacaoEstoque, TabelaPreco, PrecoProdutoTabela
from .forms import ProdutoForm, ProdutoCSVImportForm, EntradaEstoqueForm, CategoriaForm, TabelaPrecoForm, PrecoProdutoTabelaForm
import csv
import io
from decimal import Decimal

class ProdutoListView(LoginRequiredMixin, ListView):
    model = Produto
    template_name = 'catalogo/produto_list.html'
    context_object_name = 'produtos'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '')
        status = self.request.GET.get('status', '')
        marca = self.request.GET.get('marca', '')
        categoria = self.request.GET.get('categoria', '')
        
        compat_marca = self.request.GET.get('compat_marca', '')
        compat_modelo = self.request.GET.get('compat_modelo', '')
        compat_ano = self.request.GET.get('compat_ano', '')
        
        if q:
            queryset = queryset.filter(
                Q(sku__icontains=q) |
                Q(nome__icontains=q) |
                Q(marca__icontains=q) |
                Q(ncm__icontains=q) |
                Q(codigo_fabricante__icontains=q) |
                Q(codigo_barras_ean__icontains=q) |
                Q(compatibilidades__marca_carro__icontains=q) |
                Q(compatibilidades__modelo_carro__icontains=q) |
                Q(compatibilidades__ano_carro__icontains=q)
            )
        else:
            # Se não houver busca, lista apenas produtos pai ou simples (sem pai)
            queryset = queryset.filter(parent__isnull=True)
            
        if status:
            if status == 'ok':
                queryset = queryset.filter(quantidade_estoque__gt=F('estoque_minimo'))
            elif status == 'low':
                queryset = queryset.filter(quantidade_estoque__gt=0, quantidade_estoque__lte=F('estoque_minimo'))
            elif status == 'out':
                queryset = queryset.filter(quantidade_estoque=0)
                
        if marca:
            queryset = queryset.filter(marca=marca)
            
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)

        # Advanced FIPE Vehicle Compatibility Filtering
        if compat_marca:
            queryset = queryset.filter(compatibilidades__marca_carro__iexact=compat_marca)
        if compat_modelo:
            queryset = queryset.filter(compatibilidades__modelo_carro__iexact=compat_modelo)
        if compat_ano and compat_ano != 'Todos os anos':
            queryset = queryset.filter(compatibilidades__ano_carro__icontains=compat_ano)
            
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate statistics
        all_produtos = Produto.objects.all()
        context['total_produtos'] = all_produtos.count()
        context['estoque_baixo'] = all_produtos.filter(
            quantidade_estoque__gt=0,
            quantidade_estoque__lte=F('estoque_minimo')
        ).count()
        context['esgotados'] = all_produtos.filter(quantidade_estoque=0).count()
        
        # Total stock valuation
        valuation = all_produtos.annotate(
            total_item=F('preco_venda') * F('quantidade_estoque')
        ).aggregate(total=Sum('total_item'))['total']
        context['valor_total_estoque'] = valuation or 0.00
        
        # Distinct brands for the filter dropdown
        context['marcas'] = Produto.objects.exclude(marca='').values_list('marca', flat=True).distinct().order_by('marca')
        
        # Categories list
        context['categorias'] = Categoria.objects.all()
        
        # Tabelas de Preço list
        context['tabelas_preco'] = TabelaPreco.objects.all()
        
        # Parameters to persist in pagination/filtering UI
        context['q'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['marca_filter'] = self.request.GET.get('marca', '')
        context['categoria_filter'] = self.request.GET.get('categoria', '')
        
        # FIPE vehicle compatibility active filters
        context['compat_marca_filter'] = self.request.GET.get('compat_marca', '')
        context['compat_modelo_filter'] = self.request.GET.get('compat_modelo', '')
        context['compat_ano_filter'] = self.request.GET.get('compat_ano', '')
        return context

class ProdutoCreateView(LoginRequiredMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'catalogo/produto_form.html'
    success_url = reverse_lazy('estoque-listar')

    def form_valid(self, form):
        response = super().form_valid(form)
        for tabela in TabelaPreco.objects.all():
            field_name = f'preco_tabela_{tabela.id}'
            preco_val = self.request.POST.get(field_name)
            if preco_val:
                try:
                    preco_val = Decimal(preco_val.replace(',', '.'))
                    if preco_val > 0:
                        PrecoProdutoTabela.objects.update_or_create(
                            tabela=tabela,
                            produto=self.object,
                            defaults={'preco_venda': preco_val}
                        )
                except (ValueError, TypeError, Decimal.InvalidOperation):
                    pass
        messages.success(self.request, f"Produto '{self.object.nome}' cadastrado com sucesso!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Cadastrar Nova Autopeça"
        context['botao_label'] = "Salvar Cadastro"
        context['tabelas_preco'] = TabelaPreco.objects.all()
        context['precos_customizados'] = {}
        return context

class ProdutoUpdateView(LoginRequiredMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'catalogo/produto_form.html'
    success_url = reverse_lazy('estoque-listar')

    def form_valid(self, form):
        response = super().form_valid(form)
        for tabela in TabelaPreco.objects.all():
            field_name = f'preco_tabela_{tabela.id}'
            preco_val = self.request.POST.get(field_name)
            if preco_val:
                try:
                    preco_val = Decimal(preco_val.replace(',', '.'))
                    if preco_val > 0:
                        PrecoProdutoTabela.objects.update_or_create(
                            tabela=tabela,
                            produto=self.object,
                            defaults={'preco_venda': preco_val}
                        )
                    else:
                        PrecoProdutoTabela.objects.filter(tabela=tabela, produto=self.object).delete()
                except (ValueError, TypeError, Decimal.InvalidOperation):
                    pass
            else:
                PrecoProdutoTabela.objects.filter(tabela=tabela, produto=self.object).delete()
        messages.success(self.request, f"Produto '{self.object.nome}' atualizado com sucesso!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editar: {self.object.nome}"
        context['botao_label'] = "Salvar Alterações"
        context['tabelas_preco'] = TabelaPreco.objects.all()
        
        precos_dict = {
            p.tabela_id: float(p.preco_venda) 
            for p in PrecoProdutoTabela.objects.filter(produto=self.object)
        }
        context['precos_customizados'] = precos_dict
        return context

class ProdutoDeleteView(LoginRequiredMixin, DeleteView):
    model = Produto
    template_name = 'catalogo/produto_confirm_delete.html'
    success_url = reverse_lazy('estoque-listar')


class ProdutoBulkActionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        product_ids = request.POST.getlist('selected_products')
        
        if not product_ids:
            messages.warning(request, "Nenhum produto foi selecionado para ação em lote.")
            return redirect('estoque-listar')
            
        if action == 'delete':
            deleted_count, _ = Produto.objects.filter(id__in=product_ids).delete()
            messages.success(request, f"{deleted_count} autopeças foram excluídas com sucesso.")
            
        return redirect('estoque-listar')


class ProdutoImportCSVView(LoginRequiredMixin, View):
    template_name = 'catalogo/produto_import_csv.html'
    
    def get(self, request, *args, **kwargs):
        form = ProdutoCSVImportForm()
        return render(request, self.template_name, {'form': form})
        
    def post(self, request, *args, **kwargs):
        form = ProdutoCSVImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})
            
        csv_file = request.FILES['arquivo_csv']
        
        # Read file with fallback encodings
        content = None
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1']:
            try:
                content = csv_file.read().decode(encoding)
                break
            except UnicodeDecodeError:
                csv_file.seek(0)
                continue
                
        if content is None:
            messages.error(request, "Não foi possível ler o arquivo com as codificações suportadas (UTF-8, ISO-8859-1).")
            return render(request, self.template_name, {'form': form})
            
        io_string = io.StringIO(content)
        
        # Detect delimiter
        first_line = io_string.readline()
        delimiter = ';' if ';' in first_line else ','
        io_string.seek(0)
        
        reader = csv.DictReader(io_string, delimiter=delimiter)
        
        # Normalize header fields to lowercase and strip whitespaces
        if reader.fieldnames:
            reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]
        else:
            reader.fieldnames = []
            
        # Required headers check
        required_headers = {'sku', 'nome'}
        if not required_headers.issubset(set(reader.fieldnames)):
            messages.error(request, f"O arquivo CSV deve conter pelo menos as colunas 'sku' e 'nome'. Colunas encontradas: {', '.join(reader.fieldnames)}")
            return render(request, self.template_name, {'form': form})
            
        success_count = 0
        update_count = 0
        error_rows = []
        
        for row_idx, row in enumerate(reader, start=1):
            sku = row.get('sku', '').strip() if row.get('sku') else ''
            nome = row.get('nome', '').strip() if row.get('nome') else ''
            
            if not sku or not nome:
                error_rows.append(f"Linha {row_idx}: 'sku' ou 'nome' estão em branco.")
                continue
                      # EAN/Código de barras
            codigo_barras_ean = row.get('codigo_barras_ean', row.get('ean', '')).strip() if (row.get('codigo_barras_ean') or row.get('ean')) else ''
            marca = row.get('marca', '').strip() if row.get('marca') else ''
            ncm = row.get('ncm', '').strip() if row.get('ncm') else ''
            
            # Parse preco_custo
            preco_custo_raw = row.get('preco_custo', row.get('custo', '0')).strip() if (row.get('preco_custo') or row.get('custo')) else '0'
            preco_custo_raw = preco_custo_raw.replace('R$', '').replace(' ', '')
            if ',' in preco_custo_raw and '.' in preco_custo_raw:
                preco_custo_raw = preco_custo_raw.replace('.', '').replace(',', '.')
            elif ',' in preco_custo_raw:
                preco_custo_raw = preco_custo_raw.replace(',', '.')
                
            try:
                preco_custo = float(preco_custo_raw) if preco_custo_raw else 0.00
            except ValueError:
                error_rows.append(f"Linha {row_idx} (SKU {sku}): Preço de custo '{preco_custo_raw}' inválido.")
                continue
            
            # Parse preco_venda
            preco_raw = row.get('preco_venda', row.get('preco', '0')).strip() if (row.get('preco_venda') or row.get('preco')) else '0'
            preco_raw = preco_raw.replace('R$', '').replace(' ', '')
            if ',' in preco_raw and '.' in preco_raw:
                preco_raw = preco_raw.replace('.', '').replace(',', '.')
            elif ',' in preco_raw:
                preco_raw = preco_raw.replace(',', '.')
                
            try:
                preco_venda = float(preco_raw) if preco_raw else 0.00
            except ValueError:
                error_rows.append(f"Linha {row_idx} (SKU {sku}): Preço de venda '{preco_raw}' inválido.")
                continue
                
            # Parse quantidade_estoque
            estoque_raw = row.get('quantidade_estoque', row.get('estoque', '0')).strip() if (row.get('quantidade_estoque') or row.get('estoque')) else '0'
            try:
                quantidade_estoque = int(estoque_raw) if estoque_raw else 0
            except ValueError:
                error_rows.append(f"Linha {row_idx} (SKU {sku}): Estoque '{estoque_raw}' inválido.")
                continue
                
            # Create or update product
            try:
                produto, created = Produto.objects.update_or_create(
                    sku=sku,
                    defaults={
                        'nome': nome,
                        'codigo_barras_ean': codigo_barras_ean,
                        'marca': marca,
                        'ncm': ncm,
                        'preco_custo': preco_custo,
                        'preco_venda': preco_venda,
                        'quantidade_estoque': quantidade_estoque
                    }
                )
                if created:
                    success_count += 1
                else:
                    update_count += 1
            except Exception as e:
                error_rows.append(f"Linha {row_idx} (SKU {sku}): Erro ao salvar produto: {str(e)}")
                
        if error_rows:
            error_msg = f"Importação concluída com alguns avisos: {success_count} criados, {update_count} atualizados. Erros nas seguintes linhas: " + " | ".join(error_rows[:5])
            if len(error_rows) > 5:
                error_msg += f" ... e mais {len(error_rows) - 5} erros."
            messages.warning(request, error_msg)
        else:
            messages.success(request, f"Importação realizada com sucesso! {success_count} produtos cadastrados e {update_count} atualizados.")
            
        return redirect('estoque-listar')
 
 
@login_required
def download_csv_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_pecas.csv"'
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['sku', 'nome', 'codigo_barras_ean', 'marca', 'ncm', 'preco_custo', 'preco_venda', 'quantidade_estoque'])
    writer.writerow(['MLB-100000001', 'Amortecedor Traseiro Cofap', '7891234567891', 'Cofap', '87088000', '210,00', '380,00', '10'])
    writer.writerow(['MLB-100000002', 'Filtro de Combustível Fram', '7891234567892', 'Fram', '84212300', '25,00', '45,90', '25'])
    
    return response


class EntradaEstoqueCreateView(LoginRequiredMixin, CreateView):
    model = EntradaEstoque
    form_class = EntradaEstoqueForm
    template_name = 'catalogo/entrada_estoque_form.html'
    success_url = reverse_lazy('estoque-listar')

    def get_initial(self):
        initial = super().get_initial()
        produto_id = self.request.GET.get('produto_id')
        if produto_id:
            initial['produto'] = produto_id
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Entrada de estoque registrada e preço médio ponderado (PMP) recalculado com sucesso!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Registrar Entrada de Estoque (PMP)"
        context['botao_label'] = "Confirmar Entrada"
        
        produto_id = self.request.GET.get('produto_id')
        if produto_id:
            try:
                selected_produto = Produto.objects.get(id=produto_id)
                context['selected_produto'] = selected_produto
                context['entradas_historico'] = EntradaEstoque.objects.filter(produto=selected_produto).order_by('-data_entrada')
            except (Produto.DoesNotExist, ValueError):
                pass
                
        return context


class EntradaEstoqueDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            entrada = EntradaEstoque.objects.get(pk=pk)
            produto_id = entrada.produto.id
            entrada.delete()
            messages.success(request, "Entrada de estoque excluída com sucesso! Estoque e preço médio (PMP) recalculados.")
            return redirect(f"/produto/entrada/?produto_id={produto_id}")
        except EntradaEstoque.DoesNotExist:
            messages.error(request, "Lançamento de entrada não encontrado.")
            return redirect('estoque-listar')


class CompatibilidadeAddView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        produto_id = request.POST.get('produto_id')
        marca_carro = request.POST.get('marca_carro')
        modelo_carro = request.POST.get('modelo_carro')
        ano_carro = request.POST.get('ano_carro', '')

        if not produto_id or not marca_carro or not modelo_carro:
            return JsonResponse({'success': False, 'error': 'Campos obrigatórios ausentes.'}, status=400)

        try:
            produto = Produto.objects.get(id=produto_id)
            # Avoid duplicate mapping
            compat, created = CompatibilidadeProduto.objects.get_or_create(
                produto=produto,
                marca_carro=marca_carro,
                modelo_carro=modelo_carro,
                ano_carro=ano_carro
            )
            return JsonResponse({
                'success': True, 
                'id': compat.id, 
                'marca': compat.marca_carro, 
                'modelo': compat.modelo_carro, 
                'ano': compat.ano_carro or 'Todos os anos'
            })
        except Produto.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Produto não encontrado.'}, status=404)


class CompatibilidadeRemoveView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            compat = CompatibilidadeProduto.objects.get(pk=pk)
            compat.delete()
            return JsonResponse({'success': True})
        except CompatibilidadeProduto.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Compatibilidade não encontrada.'}, status=404)


class CompatibilidadeListView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        produto_id = request.GET.get('produto_id')
        if not produto_id:
            return JsonResponse({'success': False, 'error': 'produto_id ausente.'}, status=400)
            
        compats = CompatibilidadeProduto.objects.filter(produto_id=produto_id)
        data = [{
            'id': c.id, 
            'marca': c.marca_carro, 
            'modelo': c.modelo_carro, 
            'ano': c.ano_carro or 'Todos os anos'
        } for c in compats]
        return JsonResponse({'success': True, 'compatibilidades': data})


class ProdutoMovimentacoesView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        produto_id = request.GET.get('produto_id')
        if not produto_id:
            return JsonResponse({'success': False, 'error': 'produto_id ausente.'}, status=400)
            
        movs = MovimentacaoEstoque.objects.filter(produto_id=produto_id).order_by('-data')
        data = [{
            'data': m.data.strftime('%d/%m/%Y %H:%M'),
            'tipo': m.get_tipo_display(),
            'tipo_code': m.tipo,
            'quantidade': m.quantidade,
            'sinal': '+' if m.tipo == 'E' else '-' if m.tipo == 'S' else '',
            'saldo_anterior': m.saldo_anterior,
            'saldo_atual': m.saldo_atual,
            'custo': float(m.custo_unitario) if m.custo_unitario else 0.0,
            'descricao': m.descricao
        } for m in movs]
        return JsonResponse({'success': True, 'movimentacoes': data})


class ProdutoEtiquetasView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        product_ids = request.POST.getlist('selected_products')
        if not product_ids:
            messages.warning(request, "Nenhum produto foi selecionado para imprimir etiquetas.")
            return redirect('estoque-listar')
        
        produtos = Produto.objects.filter(id__in=product_ids)
        return render(request, 'catalogo/etiquetas_print.html', {'produtos': produtos})
        
    def get(self, request, *args, **kwargs):
        ids_str = request.GET.get('ids', '')
        if ids_str:
            ids = ids_str.split(',')
            produtos = Produto.objects.filter(id__in=ids)
            return render(request, 'catalogo/etiquetas_print.html', {'produtos': produtos})
        return redirect('estoque-listar')


class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = 'catalogo/categoria_list.html'
    context_object_name = 'categorias'
    ordering = ['nome']


class CategoriaCreateView(LoginRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'catalogo/categoria_form.html'
    success_url = reverse_lazy('categoria-listar')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Categoria '{self.object.nome}' cadastrada com sucesso!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Cadastrar Nova Categoria"
        context['botao_label'] = "Salvar Categoria"
        return context


class CategoriaUpdateView(LoginRequiredMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'catalogo/categoria_form.html'
    success_url = reverse_lazy('categoria-listar')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Categoria '{self.object.nome}' atualizada com sucesso!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editar Categoria: {self.object.nome}"
        context['botao_label'] = "Salvar Alterações"
        return context


class CategoriaDeleteView(LoginRequiredMixin, DeleteView):
    model = Categoria
    template_name = 'catalogo/categoria_confirm_delete.html'
    success_url = reverse_lazy('categoria-listar')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = self.object.nome
        self.object.delete()
        messages.success(request, f"Categoria '{nome}' excluída com sucesso! Subcategorias associadas foram removidas por cascata.")
        return redirect(self.get_success_url())


class TabelaPrecoListView(LoginRequiredMixin, ListView):
    model = TabelaPreco
    template_name = 'catalogo/tabelapreco_list.html'
    context_object_name = 'tabelas'


class TabelaPrecoCreateView(LoginRequiredMixin, CreateView):
    model = TabelaPreco
    form_class = TabelaPrecoForm
    template_name = 'catalogo/tabelapreco_form.html'
    success_url = reverse_lazy('tabelapreco-listar')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Tabela de preços '{self.object.nome}' cadastrada com sucesso!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Criar Tabela de Preço"
        context['botao_label'] = "Salvar Tabela"
        return context


class TabelaPrecoUpdateView(LoginRequiredMixin, UpdateView):
    model = TabelaPreco
    form_class = TabelaPrecoForm
    template_name = 'catalogo/tabelapreco_form.html'
    success_url = reverse_lazy('tabelapreco-listar')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Tabela de preços '{self.object.nome}' atualizada com sucesso!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editar Tabela: {self.object.nome}"
        context['botao_label'] = "Salvar Alterações"
        return context


class TabelaPrecoDeleteView(LoginRequiredMixin, DeleteView):
    model = TabelaPreco
    template_name = 'catalogo/tabelapreco_confirm_delete.html'
    success_url = reverse_lazy('tabelapreco-listar')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = self.object.nome
        self.object.delete()
        messages.success(request, f"Tabela de preços '{nome}' excluída com sucesso!")
        return redirect(self.get_success_url())


class TabelaPrecoPrecosView(LoginRequiredMixin, View):
    template_name = 'catalogo/tabelapreco_precos.html'

    def get(self, request, pk, *args, **kwargs):
        tabela = TabelaPreco.objects.get(pk=pk)
        produtos = Produto.objects.all().order_by('nome')
        
        precos_customizados = {
            p.produto_id: float(p.preco_venda)
            for p in PrecoProdutoTabela.objects.filter(tabela=tabela)
        }
        
        produtos_list = []
        for p in produtos:
            preco_calculado = float(p.preco_venda) - (float(p.preco_venda) * float(tabela.percentual_desconto_padrao) / 100.0)
            custom_preco = precos_customizados.get(p.id)
            produtos_list.append({
                'id': p.id,
                'sku': p.sku,
                'nome': p.nome,
                'preco_venda_base': float(p.preco_venda),
                'preco_calculado': preco_calculado,
                'preco_customizado': custom_preco or 0.00,
                'is_custom': custom_preco is not None and custom_preco > 0
            })

        return render(request, self.template_name, {
            'tabela': tabela,
            'produtos': produtos_list
        })

    def post(self, request, pk, *args, **kwargs):
        tabela = TabelaPreco.objects.get(pk=pk)
        
        for key, value in request.POST.items():
            if key.startswith('preco_prod_'):
                try:
                    prod_id = int(key.replace('preco_prod_', ''))
                    produto = Produto.objects.get(id=prod_id)
                    
                    if value.strip():
                        preco_val = Decimal(value.replace(',', '.'))
                        if preco_val > 0:
                            PrecoProdutoTabela.objects.update_or_create(
                                tabela=tabela,
                                produto=produto,
                                defaults={'preco_venda': preco_val}
                            )
                        else:
                            PrecoProdutoTabela.objects.filter(tabela=tabela, produto=produto).delete()
                    else:
                        PrecoProdutoTabela.objects.filter(tabela=tabela, produto=produto).delete()
                except (ValueError, TypeError, Produto.DoesNotExist, Decimal.InvalidOperation):
                    pass
                    
        messages.success(request, f"Preços da tabela '{tabela.nome}' atualizados com sucesso!")
        return redirect('tabelapreco-listar')
