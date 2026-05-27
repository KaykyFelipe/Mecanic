from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views import View
from django.urls import reverse_lazy
from django.db.models import F, Sum, Q
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import Produto
from .forms import ProdutoForm, ProdutoCSVImportForm
import csv
import io

class ProdutoListView(LoginRequiredMixin, ListView):
    model = Produto
    template_name = 'catalogo/produto_list.html'
    context_object_name = 'produtos'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '')
        if q:
            queryset = queryset.filter(
                Q(sku__icontains=q) |
                Q(nome__icontains=q) |
                Q(marca__icontains=q) |
                Q(ncm__icontains=q) |
                Q(codigo_barras_ean__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate statistics
        all_produtos = Produto.objects.all()
        context['total_produtos'] = all_produtos.count()
        context['estoque_baixo'] = all_produtos.filter(quantidade_estoque__gt=0, quantidade_estoque__lt=5).count()
        context['esgotados'] = all_produtos.filter(quantidade_estoque=0).count()
        
        # Total stock valuation
        valuation = all_produtos.annotate(
            total_item=F('preco_venda') * F('quantidade_estoque')
        ).aggregate(total=Sum('total_item'))['total']
        context['valor_total_estoque'] = valuation or 0.00
        
        context['q'] = self.request.GET.get('q', '')
        return context

class ProdutoCreateView(LoginRequiredMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'catalogo/produto_form.html'
    success_url = reverse_lazy('estoque-listar')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Cadastrar Nova Autopeça"
        context['botao_label'] = "Salvar Cadastro"
        return context

class ProdutoUpdateView(LoginRequiredMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'catalogo/produto_form.html'
    success_url = reverse_lazy('estoque-listar')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editar: {self.object.nome}"
        context['botao_label'] = "Salvar Alterações"
        return context

class ProdutoDeleteView(LoginRequiredMixin, DeleteView):
    model = Produto
    template_name = 'catalogo/produto_confirm_delete.html'
    success_url = reverse_lazy('estoque-listar')


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
                error_rows.append(f"Linha {row_idx} (SKU {sku}): Preço '{preco_raw}' inválido.")
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
    writer.writerow(['sku', 'nome', 'codigo_barras_ean', 'marca', 'ncm', 'preco_venda', 'quantidade_estoque'])
    writer.writerow(['MLB-100000001', 'Amortecedor Traseiro Cofap', '7891234567891', 'Cofap', '87088000', '380,00', '10'])
    writer.writerow(['MLB-100000002', 'Filtro de Combustível Fram', '7891234567892', 'Fram', '84212300', '45,90', '25'])
    
    return response
