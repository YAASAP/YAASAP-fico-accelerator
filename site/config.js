// Seul fichier à modifier pour brancher le paiement.
window.FICO_CONFIG = {
  // Stripe > Payment Links > créer le lien « Solo 79 €/mois », coller l'URL ici.
  stripeLinkSolo: "https://buy.stripe.com/3cIeVd3uv7pO7n4ekCgIo0n",
  // URL du worker déployé (voir worker/README.md), sans slash final.
  apiUrl: "https://fico-accelerator-api.k52pn6swmg.workers.dev",
  contact: "y.aouabed@hotmail.fr"
};
