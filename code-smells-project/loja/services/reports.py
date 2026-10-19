# Preserva faixas, ordem e inclusão dos pedidos cancelados do relatório original.
DISCOUNT_BRACKETS = ((10000, 0.10), (5000, 0.05), (1000, 0.02))


def discount_for(revenue):
    return next((revenue * rate for threshold, rate in DISCOUNT_BRACKETS if revenue > threshold), 0)


def sales_report(totals):
    revenue, count = totals['faturamento'], totals['total_pedidos']
    discount = discount_for(revenue)
    return {'total_pedidos': count, 'faturamento_bruto': round(revenue, 2),
            'desconto_aplicavel': round(discount, 2), 'faturamento_liquido': round(revenue-discount, 2),
            'pedidos_pendentes': totals['pendentes'], 'pedidos_aprovados': totals['aprovados'],
            'pedidos_cancelados': totals['cancelados'], 'ticket_medio': round(revenue/count, 2) if count else 0}
