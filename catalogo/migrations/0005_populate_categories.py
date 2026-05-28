from django.db import migrations

def populate_categories(apps, schema_editor):
    Categoria = apps.get_model('catalogo', 'Categoria')
    
    # Standard auto-parts categories mapping
    categories_tree = {
        "Motor": ["Filtros", "Ignição", "Correias & Tensores", "Cabeçote & Blocos"],
        "Suspensão & Direção": ["Amortecedores", "Molas & Batentes", "Pivôs & Terminais", "Buchas & Coxins"],
        "Sistema de Freio": ["Pastilhas de Freio", "Discos de Freio", "Cilindros & Pinças"],
        "Transmissão & Embreagem": ["Kits de Embreagem", "Juntas Homocinéticas"],
        "Elétrica & Eletrônica": ["Alternadores & Motores de Partida", "Baterias", "Cabos & Velas"],
        "Iluminação": ["Faróis", "Lanternas", "Lâmpadas"],
        "Sistema de Arrefecimento": ["Radiadores", "Bombas de Água", "Aditivos & Mangueiras"],
        "Escapamento & Exaustão": ["Silenciadores", "Catalisadores"]
    }
    
    for parent_name, children in categories_tree.items():
        parent, created = Categoria.objects.get_or_create(nome=parent_name)
        for child_name in children:
            Categoria.objects.get_or_create(nome=child_name, parent=parent)

def rollback_categories(apps, schema_editor):
    Categoria = apps.get_model('catalogo', 'Categoria')
    Categoria.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0004_categoria_produto_categoria_compatibilidadeproduto_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_categories, rollback_categories),
    ]
