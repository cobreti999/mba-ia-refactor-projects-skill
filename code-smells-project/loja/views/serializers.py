PRODUCT_FIELDS = ('id', 'nome', 'descricao', 'preco', 'estoque', 'categoria', 'ativo', 'criado_em')
USER_FIELDS = ('id', 'nome', 'email', 'tipo', 'criado_em')


def product(row):
    return {field: row[field] for field in PRODUCT_FIELDS}


def user(row):
    return {field: row[field] for field in USER_FIELDS}


def order(row, items):
    data = {field: row[field] for field in ('id', 'usuario_id', 'status', 'total', 'criado_em')}
    data['itens'] = [
        {'produto_id': item['produto_id'], 'produto_nome': item['produto_nome'] or 'Desconhecido',
         'quantidade': item['quantidade'], 'preco_unitario': item['preco_unitario']}
        for item in items
    ]
    return data
