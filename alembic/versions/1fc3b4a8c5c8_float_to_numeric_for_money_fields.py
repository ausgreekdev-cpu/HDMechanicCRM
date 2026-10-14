"""float to numeric for money fields

Revision ID: 1fc3b4a8c5c8
Revises: d05e2ae51680
Create Date: 2026-07-27 14:48:51.799218

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fc3b4a8c5c8'
down_revision: Union[str, Sequence[str], None] = 'd05e2ae51680'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert money columns from Float to Numeric(10, 2)."""
    with op.batch_alter_table('bank_accounts') as batch_op:
        batch_op.alter_column('balance', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('bank_transactions') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=False)
    with op.batch_alter_table('budgets') as batch_op:
        batch_op.alter_column('budgeted_amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('consignment_items') as batch_op:
        batch_op.alter_column('unit_cost', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('contractors_1099') as batch_op:
        batch_op.alter_column('total_paid_ytd', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('core_charges') as batch_op:
        batch_op.alter_column('charge_amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('core_returns') as batch_op:
        batch_op.alter_column('refund_amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('credit_memos') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=False)
    with op.batch_alter_table('customer_deposits') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=False)
        batch_op.alter_column('balance', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=False)
    with op.batch_alter_table('daily_metrics') as batch_op:
        batch_op.alter_column('revenue', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('diesel_emission_records') as batch_op:
        batch_op.alter_column('cost', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('environmental_records') as batch_op:
        batch_op.alter_column('cost', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('estimate_items') as batch_op:
        batch_op.alter_column('total_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('unit_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('estimates') as batch_op:
        batch_op.alter_column('labor_hours', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('labor_rate', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('parts_total', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('total_amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('expenses') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=False)
    with op.batch_alter_table('fuel_records') as batch_op:
        batch_op.alter_column('price_per_gallon', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('total_cost', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.alter_column('amount_paid', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('subtotal', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('tax_amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('tax_rate', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('total_amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('kit_assemblies') as batch_op:
        batch_op.alter_column('selling_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('late_fee_rules') as batch_op:
        batch_op.alter_column('fee_value', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('max_fee', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('non_stock_items') as batch_op:
        batch_op.alter_column('estimated_cost', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('selling_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('parts') as batch_op:
        batch_op.alter_column('cost_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('selling_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('payments') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=False)
    with op.batch_alter_table('purchase_order_items') as batch_op:
        batch_op.alter_column('total_cost', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('unit_cost', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('recurring_work_orders') as batch_op:
        batch_op.alter_column('labor_hours', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('labor_rate', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('scrap_inventory') as batch_op:
        batch_op.alter_column('estimated_value', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('scrap_pickups') as batch_op:
        batch_op.alter_column('price_per_kg', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('total_payout', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('shop_supplies') as batch_op:
        batch_op.alter_column('cost_per_unit', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('subscription_plans') as batch_op:
        batch_op.alter_column('price_monthly', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=False)
        batch_op.alter_column('price_yearly', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=False)
    with op.batch_alter_table('technicians') as batch_op:
        batch_op.alter_column('hourly_rate', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('template_purchases') as batch_op:
        batch_op.alter_column('amount_paid', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=False)
    with op.batch_alter_table('tpm_contracts') as batch_op:
        batch_op.alter_column('monthly_fee', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('vendor_quotes') as batch_op:
        batch_op.alter_column('total_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('unit_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('warranty_claims') as batch_op:
        batch_op.alter_column('labor_cost', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('parts_cost', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('total_claim', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('work_order_items') as batch_op:
        batch_op.alter_column('total_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('unit_price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('work_orders') as batch_op:
        batch_op.alter_column('labor_hours', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('labor_rate', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('parts_total', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
        batch_op.alter_column('total_amount', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)
    with op.batch_alter_table('workflow_templates') as batch_op:
        batch_op.alter_column('price', existing_type=sa.Float(), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)


def downgrade() -> None:
    """Revert money columns to Float."""
    with op.batch_alter_table('bank_accounts') as batch_op:
        batch_op.alter_column('balance', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('bank_transactions') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=False)
    with op.batch_alter_table('budgets') as batch_op:
        batch_op.alter_column('budgeted_amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('consignment_items') as batch_op:
        batch_op.alter_column('unit_cost', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('contractors_1099') as batch_op:
        batch_op.alter_column('total_paid_ytd', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('core_charges') as batch_op:
        batch_op.alter_column('charge_amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('core_returns') as batch_op:
        batch_op.alter_column('refund_amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('credit_memos') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=False)
    with op.batch_alter_table('customer_deposits') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('balance', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=False)
    with op.batch_alter_table('daily_metrics') as batch_op:
        batch_op.alter_column('revenue', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('diesel_emission_records') as batch_op:
        batch_op.alter_column('cost', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('environmental_records') as batch_op:
        batch_op.alter_column('cost', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('estimate_items') as batch_op:
        batch_op.alter_column('total_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('unit_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('estimates') as batch_op:
        batch_op.alter_column('labor_hours', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('labor_rate', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('parts_total', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('total_amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('expenses') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=False)
    with op.batch_alter_table('fuel_records') as batch_op:
        batch_op.alter_column('price_per_gallon', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('total_cost', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.alter_column('amount_paid', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('subtotal', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('tax_amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('tax_rate', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('total_amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('kit_assemblies') as batch_op:
        batch_op.alter_column('selling_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('late_fee_rules') as batch_op:
        batch_op.alter_column('fee_value', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('max_fee', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('non_stock_items') as batch_op:
        batch_op.alter_column('estimated_cost', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('selling_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('parts') as batch_op:
        batch_op.alter_column('cost_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('selling_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('payments') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=False)
    with op.batch_alter_table('purchase_order_items') as batch_op:
        batch_op.alter_column('total_cost', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('unit_cost', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('recurring_work_orders') as batch_op:
        batch_op.alter_column('labor_hours', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('labor_rate', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('scrap_inventory') as batch_op:
        batch_op.alter_column('estimated_value', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('scrap_pickups') as batch_op:
        batch_op.alter_column('price_per_kg', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('total_payout', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('shop_supplies') as batch_op:
        batch_op.alter_column('cost_per_unit', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('subscription_plans') as batch_op:
        batch_op.alter_column('price_monthly', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('price_yearly', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=False)
    with op.batch_alter_table('technicians') as batch_op:
        batch_op.alter_column('hourly_rate', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('template_purchases') as batch_op:
        batch_op.alter_column('amount_paid', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=False)
    with op.batch_alter_table('tpm_contracts') as batch_op:
        batch_op.alter_column('monthly_fee', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('vendor_quotes') as batch_op:
        batch_op.alter_column('total_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('unit_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('warranty_claims') as batch_op:
        batch_op.alter_column('labor_cost', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('parts_cost', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('total_claim', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('work_order_items') as batch_op:
        batch_op.alter_column('total_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('unit_price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('work_orders') as batch_op:
        batch_op.alter_column('labor_hours', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('labor_rate', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('parts_total', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('total_amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
    with op.batch_alter_table('workflow_templates') as batch_op:
        batch_op.alter_column('price', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Float(), existing_nullable=True)
