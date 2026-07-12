from decimal import Decimal

from django.test import SimpleTestCase

from .forms import OrderCreateForm
from .models import Order


class OrderBusinessRuleTests(SimpleTestCase):
    def test_order_form_does_not_expose_manual_delivery_address_field(self):
        form = OrderCreateForm()
        self.assertNotIn('delivery_address', form.fields)

    def test_delivery_charge_is_free_for_first_five_km(self):
        self.assertEqual(Order.calculate_delivery_charge(Decimal('4.9')), Decimal('0.00'))
        self.assertEqual(Order.calculate_delivery_charge(Decimal('5.0')), Decimal('0.00'))

    def test_delivery_charge_uses_fixed_fee_per_10km_block_after_five_km(self):
        self.assertEqual(Order.calculate_delivery_charge(Decimal('6.0')), Decimal('25.00'))
        self.assertEqual(Order.calculate_delivery_charge(Decimal('15.0')), Decimal('25.00'))
        self.assertEqual(Order.calculate_delivery_charge(Decimal('16.0')), Decimal('50.00'))

    def test_cancel_is_blocked_for_delivery_orders_after_mailed_or_out_for_delivery(self):
        delivery_order = Order(status='mailed', delivery_option='delivery')
        self.assertFalse(delivery_order.can_cancel())

        delivery_order = Order(status='out_for_delivery', delivery_option='delivery')
        self.assertFalse(delivery_order.can_cancel())

        pickup_order = Order(status='ready_for_pickup', delivery_option='pickup')
        self.assertTrue(pickup_order.can_cancel())
