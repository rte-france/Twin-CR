<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=messagesPerField.exists('global') displayInfo=realm.password && realm.registrationAllowed && !usernameEditDisabled??; section>
    <#if section = "header">
    <#elseif section = "form">

        <div class="login-wrapper-root">
            <div class="login-container">
                <div class="form-side">
                    <div class="form-content-inner">
                        <!-- Logo aligné à gauche avec la carte -->
                        <div class="brand-logo">TwinEu</div>

                        <h1 class="form-title">Update Password</h1>

                        <form id="kc-passwd-update-form" class="${properties.kcFormClass!}" action="${url.loginAction}" method="post">

                            <input type="text" id="username" name="username" value="${username}" autocomplete="username" readonly style="display:none;" />
                            <input type="password" id="password" name="password" autocomplete="current-password" style="display:none;" />

                            <div class="input-group">
                                <label for="password-new" class="input-label">${msg("passwordNew")}</label>
                                <div class="input-wrapper">
                                    <input tabindex="1" id="password-new" class="custom-input" name="password-new" type="password" autofocus autocomplete="new-password" placeholder="Enter New Password" />
                                </div>
                            </div>

                            <div class="input-group">
                                <label for="password-confirm" class="input-label">${msg("passwordConfirm")}</label>
                                <div class="input-wrapper">
                                    <input tabindex="2" id="password-confirm" class="custom-input" name="password-confirm" type="password" autocomplete="new-password" placeholder="Confirm New Password" />
                                </div>
                            </div>

                            <div id="kc-form-buttons" class="form-group" style="margin-top: 2rem;">
                                <input tabindex="3" class="submit-btn" name="save" id="kc-save" type="submit" value="UPDATE PASSWORD" />
                            </div>
                        </form>

                        <div class="support-text">
                            Connection problem? Contact Twin-Eu personnel
                        </div>
                    </div>
                </div>

                <div class="visual-side">
                    <svg class="grain-overlay" xmlns="http://www.w3.org/2000/svg">
                        <filter id="noiseFilter">
                            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch" />
                        </filter>
                        <rect width="100%" height="100%" filter="url(#noiseFilter)" />
                    </svg>

                    <div class="visual-content">
                        <div class="svg-container">
                            <svg viewBox="0 0 1000 1000">
                                <defs>
                                    <linearGradient id="blue-grad-1" x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" stop-color="#001a4d" />
                                        <stop offset="30%" stop-color="#0055ff" />
                                        <stop offset="70%" stop-color="#66aaff" />
                                        <stop offset="100%" stop-color="#ffffff" />
                                    </linearGradient>
                                    <linearGradient id="blue-grad-2" x1="100%" y1="0%" x2="0%" y2="100%">
                                        <stop offset="0%" stop-color="#002266" />
                                        <stop offset="50%" stop-color="#0077ff" />
                                        <stop offset="100%" stop-color="#b3d4ff" />
                                    </linearGradient>
                                </defs>
                                <circle class="ring ring-1" cx="500" cy="500" r="220" />
                                <circle class="ring ring-2" cx="500" cy="500" r="320" />
                                <circle class="ring ring-3" cx="500" cy="500" r="450" />
                            </svg>
                        </div>

                        <div class="promo-text">
                            <p>A new way to experience real estate<br>in the infinite virtual space.</p>
                            <a href="#" class="learn-more">LEARN MORE</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <style>
            .login-wrapper-root {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                z-index: 9999;
                background-color: #000000;
                font-family: system-ui, -apple-system, sans-serif;
                color: #ffffff;
                overflow: hidden;
            }

            .login-wrapper-root * {
                box-sizing: border-box;
            }

            .login-container {
                display: flex;
                width: 100%;
                height: 100%;
                background: linear-gradient(135deg, #020617, #0a1128, #000000, #091a3a);
                background-size: 400% 400%;
                animation: gradientBackground 15s ease infinite;
            }

            @keyframes gradientBackground {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            /* Layout 1/3 pour le formulaire */
            .form-side {
                flex: 0 0 33.3333%;
                max-width: 33.3333%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding: 2rem;
                z-index: 30;
                background: rgba(0, 0, 0, 0.4);
                height: 100%;
                overflow-y: auto;
            }

            .form-content-inner {
                width: 100%;
                max-width: 380px;
                display: flex;
                flex-direction: column;
            }

            .brand-logo {
                font-size: 1.2rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                background: linear-gradient(90deg, #60a5fa, #3b82f6, #93c5fd);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 2rem;
                width: 100%;
                text-align: left;
            }

            .form-title {
                font-size: 2.3rem;
                font-weight: 500;
                margin-bottom: 2rem;
                letter-spacing: -0.03em;
            }

            .input-group {
                margin-bottom: 1.5rem;
                display: flex;
                flex-direction: column;
            }

            .input-label {
                font-size: 0.85rem;
                margin-bottom: 0.5rem;
                color: #cccccc;
            }

            .custom-input {
                width: 100%;
                padding: 0.9rem 1rem;
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
                color: #ffffff;
                font-size: 0.95rem;
                outline: none;
                transition: border-color 0.2s, box-shadow 0.2s;
            }

            .custom-input:focus {
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
            }

            .submit-btn {
                width: 100%;
                padding: 0.9rem;
                background: linear-gradient(270deg, #2563eb, #3b82f6, #1d4ed8, #60a5fa);
                background-size: 300% 300%;
                animation: buttonGradient 6s ease infinite;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.3s, filter 0.3s;
            }

            .submit-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 25px rgba(59, 130, 246, 0.5);
                filter: brightness(1.15);
            }

            @keyframes buttonGradient {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            .support-text {
                margin-top: 1.5rem;
                font-size: 0.75rem;
                color: #64748b;
                letter-spacing: 0.02em;
            }

            /* Layout 2/3 pour la partie visuelle */
            .visual-side {
                flex: 0 0 66.6666%;
                max-width: 66.6666%;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                height: 100%;
            }

            .grain-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 20;
                opacity: 0.25;
                mix-blend-mode: color-dodge;
            }

            .visual-content {
                position: relative;
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .svg-container {
                width: 600px;
                height: 600px;
                position: absolute;
                filter: drop-shadow(0 0 25px rgba(0, 85, 255, 0.3));
            }

            .svg-container svg {
                width: 100%;
                height: 100%;
            }

            .ring {
                fill: none;
                transform-origin: center;
            }

            .ring-1 {
                stroke: url(#blue-grad-1);
                stroke-width: 40;
                stroke-dasharray: 120 150 200 120 300 110;
                animation: spin 14s linear infinite;
            }

            .ring-2 {
                stroke: url(#blue-grad-2);
                stroke-width: 60;
                stroke-dasharray: 250 200 150 300 400 200;
                animation: spin-reverse 20s linear infinite;
            }

            .ring-3 {
                stroke: url(#blue-grad-1);
                stroke-width: 90;
                stroke-dasharray: 450 300 250 400 500 200;
                animation: spin 28s linear infinite;
            }

            .promo-text {
                position: absolute;
                top: 20%;
                left: 10%;
                z-index: 25;
            }

            .promo-text p {
                font-size: 1.1rem;
                line-height: 1.5;
                color: #e2e8f0;
                margin-bottom: 1rem;
            }

            .learn-more {
                font-size: 0.75rem;
                letter-spacing: 0.1em;
                color: #ffffff;
                text-decoration: none;
                font-weight: 600;
                border-bottom: 1px solid #ffffff;
                padding-bottom: 2px;
            }

            @keyframes spin {
                100% { transform: rotate(360deg); }
            }

            @keyframes spin-reverse {
                100% { transform: rotate(-360deg); }
            }

            @media (max-width: 900px) {
                .form-side {
                    flex: 0 0 100%;
                    max-width: 100%;
                    padding: 2rem 5%;
                }
                .visual-side {
                    display: none;
                }
            }
        </style>
    </#if>
</@layout.registrationLayout>
