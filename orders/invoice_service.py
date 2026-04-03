"""
Invoice Generation Service

Generates professional PDF invoices for orders after successful payment.
Uses ReportLab for PDF generation and supports both local and cloud storage.

Features:
- Professional invoice format
- Customer details
- Order items with pricing
- Tax and total calculations
- Payment details
- Stores invoice reference in database
- Cloud storage support (Cloudinary)
"""

import io
import logging
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from .models import Invoice

logger = logging.getLogger(__name__)


class InvoiceGenerator:
    """
    Generate professional PDF invoices for orders.
    Stores invoice in database and file system (or cloud).
    """

    def __init__(self):
        """Initialize invoice generator settings."""
        self.page_size = A4
        self.margin = 0.5 * inch
        self.width, self.height = self.page_size

    def generate_invoice(self, order):
        """
        Generate PDF invoice for an order.
        
        Args:
            order: Order instance to generate invoice for
            
        Returns:
            Invoice: Created/updated Invoice instance with PDF file
        """
        try:
            # Create PDF content
            pdf_content = self._create_pdf_content(order)

            # Create or update Invoice record
            invoice, created = Invoice.objects.get_or_create(order=order)

            # Generate unique invoice number if not already set
            if not invoice.invoice_number:
                invoice.invoice_number = self._generate_invoice_number(order)

            # Save PDF file
            filename = f"INV-{invoice.invoice_number}.pdf"
            invoice.pdf_file.save(
                filename,
                ContentFile(pdf_content),
                save=True
            )

            logger.info(f"Invoice generated successfully for order {order.order_number}")
            return invoice

        except Exception as e:
            logger.error(f"Error generating invoice for order {order.order_number}: {str(e)}")
            raise

    def _create_pdf_content(self, order):
        """
        Create PDF content as bytes.
        
        Args:
            order: Order instance
            
        Returns:
            bytes: PDF file content
        """
        # Create in-memory PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )

        # Container for PDF elements
        elements = []

        # Add invoice header
        elements.extend(self._create_header(order))

        # Add customer details
        elements.extend(self._create_customer_details(order))

        # Add invoice items table
        elements.extend(self._create_items_table(order))

        # Add totals section
        elements.extend(self._create_totals_section(order))

        # Add footer
        elements.extend(self._create_footer(order))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def _create_header(self, order):
        """Create invoice header with company/store details."""
        elements = []
        styles = getSampleStyleSheet()

        # Store name
        store_title = Paragraph(
            f"<b>Invoice</b>",
            ParagraphStyle(name='StoreTitle', fontSize=24, textColor=colors.HexColor('#1a1a1a'), spaceAfter=6)
        )
        elements.append(store_title)

        # Invoice and date details
        invoice_number = f"INV-{order.order_number}-{order.created_at.strftime('%Y%m%d')}"
        invoice_date = order.created_at.strftime('%Y-%m-%d')

        header_data = [
            [
                Paragraph(f"<b>Invoice #</b>", styles['Normal']),
                Paragraph(f"{invoice_number}", styles['Normal']),
            ],
            [
                Paragraph(f"<b>Invoice Date</b>", styles['Normal']),
                Paragraph(f"{invoice_date}", styles['Normal']),
            ],
            [
                Paragraph(f"<b>Order #</b>", styles['Normal']),
                Paragraph(f"{order.order_number}", styles['Normal']),
            ],
        ]

        header_table = Table(header_data, colWidths=[2 * inch, 2 * inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 0.3 * inch))

        return elements

    def _create_customer_details(self, order):
        """Create customer and shipping details section."""
        elements = []
        styles = getSampleStyleSheet()

        # Customer and shipping section
        customer_data = [
            [
                Paragraph("<b>BILL TO:</b>", styles['Normal']),
                Paragraph("<b>SHIP TO:</b>", styles['Normal']),
            ],
            [
                Paragraph(
                    f"{order.customer.get_full_name() or order.customer.username}<br/>"
                    f"{order.customer.email}",
                    ParagraphStyle(name='CustomerInfo', fontSize=9, leading=12)
                ),
                Paragraph(
                    f"{order.shipping_address.full_name}<br/>"
                    f"{order.shipping_address.address_line1}<br/>"
                    f"{order.shipping_address.city}, {order.shipping_address.state} {order.shipping_address.postal_code}<br/>"
                    f"{order.shipping_address.country}<br/>"
                    f"Phone: {order.shipping_address.phone}",
                    ParagraphStyle(name='ShippingInfo', fontSize=9, leading=12)
                ),
            ],
        ]

        customer_table = Table(customer_data, colWidths=[3 * inch, 3 * inch])
        customer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, 1), 10),
        ]))

        elements.append(customer_table)
        elements.append(Spacer(1, 0.3 * inch))

        return elements

    def _create_items_table(self, order):
        """Create items/products table."""
        elements = []
        styles = getSampleStyleSheet()

        # Table header
        items_data = [[
            Paragraph("<b>Product</b>", styles['Normal']),
            Paragraph("<b>Qty</b>", styles['Normal']),
            Paragraph("<b>Price</b>", styles['Normal']),
            Paragraph("<b>Amount</b>", styles['Normal']),
        ]]

        # Add order items
        for item in order.items.all():
            items_data.append([
                Paragraph(f"{item.product_name} {item.variant_details}", ParagraphStyle(
                    name='ItemName', fontSize=9, leading=11
                )),
                Paragraph(f"{item.quantity}", styles['Normal']),
                Paragraph(f"₹{item.unit_price:.2f}", styles['Normal']),
                Paragraph(f"₹{item.line_total:.2f}", styles['Normal']),
            ])

        items_table = Table(
            items_data,
            colWidths=[3.5 * inch, 0.8 * inch, 1 * inch, 1 * inch]
        )
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
        ]))

        elements.append(items_table)
        elements.append(Spacer(1, 0.2 * inch))

        return elements

    def _create_totals_section(self, order):
        """Create pricing totals section."""
        elements = []
        styles = getSampleStyleSheet()

        totals_data = [
            [Paragraph("<b>Subtotal</b>", styles['Normal']), Paragraph(f"₹{order.subtotal:.2f}", styles['Normal'])],
            [Paragraph("<b>Shipping</b>", styles['Normal']), Paragraph(f"₹{order.shipping_cost:.2f}", styles['Normal'])],
            [Paragraph("<b>Tax (10%)</b>", styles['Normal']), Paragraph(f"₹{order.tax_amount:.2f}", styles['Normal'])],
        ]

        if order.discount_amount > 0:
            totals_data.append([
                Paragraph("<b>Discount</b>", styles['Normal']),
                Paragraph(f"-₹{order.discount_amount:.2f}", ParagraphStyle(
                    name='Discount', fontSize=10, textColor=colors.HexColor('#28a745')
                ))
            ])

        totals_data.append([
            Paragraph("<b>Total Amount</b>", ParagraphStyle(
                name='Total', fontSize=11, textColor=colors.black
            )),
            Paragraph(f"<b>₹{order.total_amount:.2f}</b>", ParagraphStyle(
                name='TotalAmount', fontSize=11, textColor=colors.HexColor('#d73b1a')
            ))
        ])

        totals_table = Table(totals_data, colWidths=[4 * inch, 1.5 * inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -2), 9),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -2), 4),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
        ]))

        elements.append(totals_table)
        elements.append(Spacer(1, 0.2 * inch))

        # Payment info
        if order.razorpay_payment:
            payment_info = Paragraph(
                f"<b>Payment Status:</b> {order.payment_status}<br/>"
                f"<b>Payment ID:</b> {order.razorpay_payment.razorpay_payment_id}",
                ParagraphStyle(name='PaymentInfo', fontSize=8, leading=10)
            )
            elements.append(payment_info)

        return elements

    def _create_footer(self, order):
        """Create invoice footer."""
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Spacer(1, 0.3 * inch))

        footer_text = Paragraph(
            f"Thank you for your order!<br/>"
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
            f"<b>Please keep this invoice for your records.</b>",
            ParagraphStyle(
                name='Footer',
                fontSize=8,
                textColor=colors.HexColor('#666666'),
                alignment=TA_CENTER,
                leading=10
            )
        )
        elements.append(footer_text)

        return elements

    def _generate_invoice_number(self, order):
        """
        Generate unique invoice number.
        
        Format: YYYY-MM-001, YYYY-MM-002, etc.
        """
        from django.utils import timezone
        
        date_prefix = timezone.now().strftime('%Y%m%d')
        
        # Get count of invoices for this date
        count = Invoice.objects.filter(
            invoice_date=timezone.now().date()
        ).count() + 1
        
        return f"{date_prefix}{count:03d}"
