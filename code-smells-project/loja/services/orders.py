from loja.database import transaction
from loja.errors import DomainError
from loja.services.validation import integer, number, order_items, ORDER_STATUSES


class OrderService:
    def __init__(self, connection, products, users, orders):
        self.connection, self.products, self.users, self.orders = connection, products, users, orders

    def create(self, user_id, items):
        integer(user_id, 'Usuario ID')
        quantities = order_items(items)
        with transaction(self.connection):
            if self.users.get(user_id) is None:
                raise DomainError('Usuário não encontrado', 404)
            selected, total = [], 0
            for product_id, quantity in quantities.items():
                product = self.products.get(product_id)
                if product is None:
                    raise DomainError(f'Produto {product_id} não encontrado')
                if product['estoque'] < quantity:
                    raise DomainError('Estoque insuficiente')
                total += product['preco'] * quantity
                selected.append((product, quantity))
            number(total, 'Total do pedido')
            order_id = self.orders.create(user_id, total)
            for product, quantity in selected:
                if not self.products.reduce_stock(product['id'], quantity):
                    raise DomainError('Estoque insuficiente')
                self.orders.add_item(order_id, product['id'], quantity, product['preco'])
        return {'pedido_id': order_id, 'total': total}

    def set_status(self, order_id, status):
        if status not in ORDER_STATUSES:
            raise DomainError('Status inválido')
        with transaction(self.connection):
            if self.orders.get(order_id) is None:
                raise DomainError('Pedido não encontrado', 404)
            self.orders.set_status(order_id, status)
