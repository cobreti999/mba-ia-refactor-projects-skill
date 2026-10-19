class ProductRepository:
    def __init__(self, connection):
        self.connection = connection

    def get(self, product_id):
        return self.connection.execute('SELECT * FROM produtos WHERE id = ?', (product_id,)).fetchone()

    def list(self, term='', category=None, minimum=None, maximum=None):
        conditions, values = [], []
        if term:
            conditions.append('(nome LIKE ? OR descricao LIKE ?)')
            values.extend([f'%{term}%', f'%{term}%'])
        if category is not None:
            conditions.append('categoria = ?')
            values.append(category)
        if minimum is not None:
            conditions.append('preco >= ?')
            values.append(minimum)
        if maximum is not None:
            conditions.append('preco <= ?')
            values.append(maximum)
        query = 'SELECT * FROM produtos'
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        return self.connection.execute(query + ' ORDER BY id', values).fetchall()

    def create(self, data):
        return self.connection.execute(
            'INSERT INTO produtos(nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)',
            tuple(data[key] for key in ('nome', 'descricao', 'preco', 'estoque', 'categoria')),
        ).lastrowid

    def update(self, product_id, data):
        self.connection.execute(
            'UPDATE produtos SET nome=?, descricao=?, preco=?, estoque=?, categoria=? WHERE id=?',
            tuple(data[key] for key in ('nome', 'descricao', 'preco', 'estoque', 'categoria')) + (product_id,),
        )

    def delete(self, product_id):
        self.connection.execute('DELETE FROM produtos WHERE id=?', (product_id,))

    def reduce_stock(self, product_id, quantity):
        return self.connection.execute(
            'UPDATE produtos SET estoque=estoque-? WHERE id=? AND estoque>=?',
            (quantity, product_id, quantity),
        ).rowcount == 1
