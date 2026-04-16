import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from flask import current_app, url_for

class EmailService:
    def __init__(self):
        # Get configuration from Flask app config (which loads from environment)
        self.smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        self.smtp_port = current_app.config.get('MAIL_PORT', 587)
        self.email = current_app.config.get('MAIL_USERNAME')
        self.password = current_app.config.get('MAIL_PASSWORD')
        self.use_tls = current_app.config.get('MAIL_USE_TLS', True)
        self.use_ssl = current_app.config.get('MAIL_USE_SSL', False)
        self.default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', self.email)
        
        # Debug logging
        current_app.logger.info(f"Email Service Initialized:")
        current_app.logger.info(f"MAIL_SERVER: {self.smtp_server}")
        current_app.logger.info(f"MAIL_PORT: {self.smtp_port}")
        current_app.logger.info(f"MAIL_USERNAME: {self.email}")
        current_app.logger.info(f"MAIL_USE_TLS: {self.use_tls}")
        current_app.logger.info(f"MAIL_USE_SSL: {self.use_ssl}")
        current_app.logger.info(f"MAIL_PASSWORD configured: {'Yes' if self.password else 'No'}")
    
    def _create_smtp_connection(self):
        """Create SMTP connection with proper configuration"""
        try:
            if self.use_ssl:
                # Use SSL connection
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
                current_app.logger.info("Using SMTP_SSL connection")
            else:
                # Use regular SMTP with optional TLS
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                current_app.logger.info("Using SMTP connection")
                
                if self.use_tls:
                    server.starttls()
                    current_app.logger.info("TLS enabled")
            
            # Login to server
            if self.email and self.password:
                server.login(self.email, self.password)
                current_app.logger.info("SMTP login successful")
            else:
                raise ValueError("Email credentials not configured")
            
            return server
            
        except smtplib.SMTPAuthenticationError as e:
            current_app.logger.error(f"SMTP Authentication failed: {str(e)}")
            raise ValueError(f"Email authentication failed. Please check your email credentials. Error: {str(e)}")
        except smtplib.SMTPConnectError as e:
            current_app.logger.error(f"SMTP Connection failed: {str(e)}")
            raise ValueError(f"Could not connect to email server. Please check server settings. Error: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"SMTP Error: {str(e)}")
            raise ValueError(f"Email configuration error: {str(e)}")
    
    def send_donation_confirmation(self, donatur_email, donatur_name, invoice, certificate_filename):
        """Send donation confirmation email with certificate link"""
        try:
            # Validate configuration
            if not self.email or not self.password:
                raise ValueError("Email credentials not configured. Please check MAIL_USERNAME and MAIL_PASSWORD in .env file")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.default_sender or self.email
            msg['To'] = donatur_email
            msg['Subject'] = f"Donasi Buku Anda Telah Diterima - {invoice}"
            
            # Certificate URL
            certificate_url = url_for('static', 
                                    filename=f'public/sertifikat-donasi/{certificate_filename}', 
                                    _external=True)
            
            # HTML email content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Donasi Buku Diterima</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                        color: white;
                        padding: 30px;
                        text-align: center;
                        border-radius: 10px 10px 0 0;
                    }}
                    .content {{
                        background: #f8fafc;
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                        border: 1px solid #e5e7eb;
                    }}
                    .highlight {{
                        background: #dbeafe;
                        padding: 15px;
                        border-radius: 8px;
                        margin: 20px 0;
                        border-left: 4px solid #3b82f6;
                    }}
                    .certificate-link {{
                        background: #10b981;
                        color: white;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 6px;
                        display: inline-block;
                        margin: 15px 0;
                        font-weight: bold;
                    }}
                    .certificate-link:hover {{
                        background: #059669;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #e5e7eb;
                        color: #6b7280;
                        font-size: 14px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎉 Donasi Buku Anda Telah Diterima!</h1>
                    <p>Terima kasih atas kontribusi Anda untuk pendidikan</p>
                </div>
                
                <div class="content">
                    <p>Yth. <strong>{donatur_name}</strong>,</p>
                    
                    <p>Kami dengan senang hati memberitahukan bahwa donasi buku Anda telah kami terima dan diverifikasi oleh tim kami.</p>
                    
                    <div class="highlight">
                        <h3>📋 Detail Donasi:</h3>
                        <p><strong>Invoice:</strong> {invoice}</p>
                        <p><strong>Status:</strong> ✅ Diterima dan Diverifikasi</p>
                    </div>
                    
                    <p>Sebagai bentuk apresiasi, kami telah menyiapkan <strong>Sertifikat Donasi</strong> untuk Anda:</p>
                    
                    <div style="text-align: center;">
                        <a href="{certificate_url}" class="certificate-link" target="_blank">
                            📜 Unduh Sertifikat Donasi
                        </a>
                    </div>
                    
                    <p>Sertifikat ini dapat Anda gunakan sebagai:</p>
                    <ul>
                        <li>Bukti kontribusi sosial untuk keperluan CSR</li>
                        <li>Dokumentasi kegiatan filantropi</li>
                        <li>Portofolio kegiatan sosial</li>
                    </ul>
                    
                    <p>Buku-buku yang Anda donasikan akan disalurkan ke perpustakaan desa di seluruh wilayah Lumajang untuk mendukung program literasi masyarakat.</p>
                    
                    <div class="highlight">
                        <p><strong>💡 Tahukah Anda?</strong></p>
                        <p>Donasi Anda telah membantu meningkatkan akses pendidikan dan literasi di desa-desa Lumajang. Setiap buku yang Anda berikan akan dibaca oleh puluhan bahkan ratusan orang!</p>
                    </div>
                    
                    <p>Sekali lagi, terima kasih atas kepedulian dan kontribusi Anda. Mari bersama-sama membangun Indonesia yang lebih cerdas melalui literasi!</p>
                    
                    <p>Salam hangat,<br>
                    <strong>Tim Donasi Buku Perpus Lumajang</strong></p>
                </div>
                
                <div class="footer">
                    <p>Email ini dikirim secara otomatis. Jika Anda memiliki pertanyaan, silakan hubungi tim kami.</p>
                    <p>© Donasi Buku Perpus Lumajang. Semua hak cipta dilindungi.</p>
                </div>
            </body>
            </html>
            """
            
            # Plain text alternative
            text_content = f"""
            Yth. {donatur_name},

            Kami dengan senang hati memberitahukan bahwa donasi buku Anda telah kami terima dan diverifikasi.

            Detail Donasi:
            - Invoice: {invoice}
            - Status: Diterima dan Diverifikasi

            Sertifikat donasi Anda dapat diunduh melalui link berikut:
            {certificate_url}

            Terima kasih atas kontribusi Anda untuk pendidikan Indonesia!

            Salam hangat,
            Tim Donasi Buku Perpus Lumajang
            """
            
            # Attach both HTML and text versions
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email using the connection method
            with self._create_smtp_connection() as server:
                server.send_message(msg)
                current_app.logger.info(f"Donation confirmation email sent to {donatur_email}")
            
            return True, "Email berhasil dikirim"
            
        except Exception as e:
            current_app.logger.error(f"Error sending donation confirmation email: {str(e)}")
            return False, f"Gagal mengirim email: {str(e)}"
    
    def send_test_email(self, to_email):
        """Send test email to verify email configuration"""
        try:
            # Validate configuration
            if not self.email or not self.password:
                raise ValueError("Email credentials not configured. Please check MAIL_USERNAME and MAIL_PASSWORD in .env file")
            
            msg = MIMEMultipart('alternative')
            msg['From'] = self.default_sender or self.email
            msg['To'] = to_email
            msg['Subject'] = "Test Email - Website Donasi Buku Perpus Lumajang"
            
            # HTML version of test email
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Test Email</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                        color: white;
                        padding: 20px;
                        text-align: center;
                        border-radius: 10px 10px 0 0;
                    }}
                    .content {{
                        background: #f8fafc;
                        padding: 20px;
                        border-radius: 0 0 10px 10px;
                        border: 1px solid #e5e7eb;
                    }}
                    .config-item {{
                        background: #ffffff;
                        padding: 10px;
                        margin: 5px 0;
                        border-radius: 5px;
                        border-left: 3px solid #3b82f6;
                    }}
                    .success-badge {{
                        background: #10b981;
                        color: white;
                        padding: 5px 15px;
                        border-radius: 15px;
                        font-size: 14px;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>✅ Test Email Berhasil!</h1>
                    <p><span class="success-badge">Konfigurasi Email Bekerja</span></p>
                </div>
                
                <div class="content">
                    <p><strong>Selamat!</strong> Ini adalah email test untuk memverifikasi bahwa konfigurasi email sistem Donasi Buku Perpus Lumajang sudah berfungsi dengan baik.</p>
                    
                    <h3>📧 Konfigurasi yang Digunakan:</h3>
                    <div class="config-item"><strong>MAIL_SERVER:</strong> {self.smtp_server}</div>
                    <div class="config-item"><strong>MAIL_PORT:</strong> {self.smtp_port}</div>
                    <div class="config-item"><strong>MAIL_USERNAME:</strong> {self.email}</div>
                    <div class="config-item"><strong>MAIL_USE_TLS:</strong> {self.use_tls}</div>
                    <div class="config-item"><strong>MAIL_USE_SSL:</strong> {self.use_ssl}</div>
                    
                    <p style="margin-top: 20px;"><strong>✅ Status:</strong> Semua konfigurasi email berfungsi dengan baik!</p>
                    
                    <p>Sistem sekarang siap untuk mengirim:</p>
                    <ul>
                        <li>Notifikasi konfirmasi donasi</li>
                        <li>Sertifikat donasi digital</li>
                        <li>Email komunikasi lainnya</li>
                    </ul>
                    
                    <p style="margin-top: 20px; font-style: italic; color: #6b7280;">
                        Email ini dikirim secara otomatis dari sistem Website Donasi Buku Perpus Lumajang untuk keperluan testing konfigurasi.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_body = f"""
            ✅ TEST EMAIL BERHASIL - Website Donasi Buku Perpus Lumajang
            
            Selamat! Ini adalah email test untuk memverifikasi konfigurasi email.
            
            Konfigurasi yang digunakan:
            - MAIL_SERVER: {self.smtp_server}
            - MAIL_PORT: {self.smtp_port}
            - MAIL_USERNAME: {self.email}
            - MAIL_USE_TLS: {self.use_tls}
            - MAIL_USE_SSL: {self.use_ssl}
            
            ✅ Status: Semua konfigurasi email berfungsi dengan baik!
            
            Sistem sekarang siap untuk mengirim:
            - Notifikasi konfirmasi donasi
            - Sertifikat donasi digital
            - Email komunikasi lainnya
            
            Email ini dikirim secara otomatis untuk keperluan testing.
            """
            
            # Attach both versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email using the connection method
            with self._create_smtp_connection() as server:
                server.send_message(msg)
                current_app.logger.info(f"Test email sent successfully to {to_email}")
            
            return True, f"Test email berhasil dikirim ke {to_email}. Silakan cek inbox atau folder spam."
            
        except Exception as e:
            current_app.logger.error(f"Error sending test email: {str(e)}")
            return False, f"Gagal mengirim test email: {str(e)}"
