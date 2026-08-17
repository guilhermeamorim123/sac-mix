// Verifies a Stripe Checkout session, then streams the PDF.
//
// The PDF never has a public URL. It sits outside /public, so the only way to
// reach it is through this function, and the only way through this function is
// with a session id that Stripe confirms was actually paid.
//
// Requires the STRIPE_SECRET_KEY environment variable in the Vercel project.

const fs = require("fs");
const path = require("path");
const Stripe = require("stripe");

// A paid session stays valid for this long. Long enough that a buyer can come
// back for the file the next day; short enough that a shared link goes stale.
const VALID_FOR_HOURS = 72;

const FILENAME = "The-4-Hour-Listing-Week.pdf";

module.exports = async (req, res) => {
  const sessionId = req.query.session_id;

  if (!sessionId || !sessionId.startsWith("cs_")) {
    return res.status(400).json({ error: "Missing or malformed session_id." });
  }

  if (!process.env.STRIPE_SECRET_KEY) {
    console.error("STRIPE_SECRET_KEY is not set on this deployment.");
    return res.status(500).json({ error: "Server is not configured." });
  }

  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

  let session;
  try {
    session = await stripe.checkout.sessions.retrieve(sessionId);
  } catch (err) {
    // A session id that Stripe does not recognise is the common case here:
    // someone guessing, or a link from a different account.
    console.warn("Stripe lookup failed:", err.message);
    return res.status(404).json({ error: "We couldn't find that order." });
  }

  if (session.payment_status !== "paid") {
    return res.status(402).json({
      error: "This order isn't marked as paid yet. If you just checked out, " +
             "give it a moment and refresh.",
    });
  }

  const ageHours = (Date.now() / 1000 - session.created) / 3600;
  if (ageHours > VALID_FOR_HOURS) {
    return res.status(410).json({
      error: "This download link has expired. Reply to your receipt email and " +
             "we'll send you a fresh one.",
    });
  }

  const file = path.join(process.cwd(), "product.pdf");
  if (!fs.existsSync(file)) {
    console.error("product.pdf is missing from the deployment bundle.");
    return res.status(500).json({ error: "The file is temporarily unavailable." });
  }

  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", `attachment; filename="${FILENAME}"`);
  res.setHeader("Cache-Control", "private, no-store");
  fs.createReadStream(file).pipe(res);
};
