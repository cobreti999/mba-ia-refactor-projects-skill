class OrderRepository:
    def __init__(self, connection):
        self.connection = connection

    def get(self, order_id):
        return self.connection.execute('SELECT * FROM pedidos WHERE id=?', (order_id,)).fetchone()

    def create(self, user_id, total):
        return self.connection.execute(
            "INSERT INTO pedidos(usuario_id,status,total) VALUES (?,'pendente',?)", (user_id, total)
        ).lastrowid

    def add_item(self, order_id, product_id, quantity, price):
        self.connection.execute(
            'INSERT INTO itens_pedido(pedido_id,produto_id,quantidade,preco_unitario) VALUES (?,?,?,?)',
            (order_id, product_id, quantity, price),
        )

    def list_with_items(self, user_id=None):
        condition = '' if user_id is None else ' WHERE p.usuario_id=?'
        values = () if user_id is None else (user_id,)
        orders = self.connection.execute('SELECT p.* FROM pedidos p' + condition + ' ORDER BY p.id', values).fetchall()
        # JOIN mantém o número de consultas fixo sem limite de placeholders por pedido.
        items = self.connection.execute('''SELECT i.*, pr.nome AS produto_nome
            FROM itens_pedido i JOIN pedidos p ON p.id=i.pedido_id
            LEFT JOIN produtos pr ON pr.id=i.produto_id''' + condition + ' ORDER BY i.id', values).fetchall()
        grouped = {}
        for item in items:
            grouped.setdefault(item['pedido_id'], []).append(item)
        return [(order, grouped.get(order['id'], [])) for order in orders]

    def set_status(self, order_id, status):
        self.connection.execute('UPDATE pedidos SET status=? WHERE id=?', (status, order_id))

    def sales_totals(self):
        return self.connection.execute('''SELECT COUNT(*) AS total_pedidos,
            COALESCE(SUM(total),0) AS faturamento,
            COALESCE(SUM(status='pendente'),0) AS pendentes,
            COALESCE(SUM(status='aprovado'),0) AS aprovados,
            COALESCE(SUM(status='cancelado'),0) AS cancelados FROM pedidos''').fetchone()
