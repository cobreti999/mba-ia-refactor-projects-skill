class AdminRepository:
    def __init__(self, connection):
        self.connection = connection

    def counts(self):
        return dict(self.connection.execute('''SELECT
            (SELECT COUNT(*) FROM produtos) AS produtos,
            (SELECT COUNT(*) FROM usuarios) AS usuarios,
            (SELECT COUNT(*) FROM pedidos) AS pedidos''').fetchone())

    def reset(self):
        for statement in ('DELETE FROM itens_pedido', 'DELETE FROM pedidos', 'DELETE FROM produtos', 'DELETE FROM usuarios'):
            self.connection.execute(statement)
