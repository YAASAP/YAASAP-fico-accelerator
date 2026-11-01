# Accès payant par e-mail

Flux : paiement Stripe → webhook → clé `FA-…` envoyée par e-mail → l'utilisateur la saisit avec son e-mail sur `acces.html` → le worker confirme. Une résiliation Stripe révoque la clé.

## Mise en ligne (≈15 min)
1. **Stripe** : créer un Payment Link « Solo 79 €/mois » (abonnement, collecte de l'e-mail activée, redirection après paiement vers `https://<site>/acces.html?paid=1`). Coller l'URL dans `site/config.js` (`stripeLinkSolo`).
2. **Resend** (ou autre) : vérifier votre domaine d'envoi, créer une clé API.
3. **Cloudflare** : `npx wrangler kv namespace create LICENCES`, reporter l'id dans `wrangler.toml` ainsi que `MAIL_FROM` et `SITE_URL`.
4. Secrets : `npx wrangler secret put LICENCE_SECRET` (chaîne aléatoire longue), `RESEND_API_KEY`, `STRIPE_WEBHOOK_SECRET`.
5. `npx wrangler deploy`, puis dans Stripe > Développeurs > Webhooks : endpoint `https://<worker>/webhook`, événements `checkout.session.completed` et `customer.subscription.deleted`, copier le secret `whsec_…` à l'étape 4.
6. Mettre l'URL du worker dans `site/config.js` (`apiUrl`).
7. GitHub : Settings > Pages > Source « GitHub Actions ». Le site `site/` se publie à chaque push.

Test local du worker : `node worker/test.mjs`.
