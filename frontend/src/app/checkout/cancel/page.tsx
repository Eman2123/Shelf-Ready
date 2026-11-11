export const metadata = { title: "Payment cancelled · ShelfReady" };

export default function CheckoutCancel() {
  return (
    <main className="mx-auto max-w-xl px-4 py-16">
      <h1 className="font-display text-5xl font-bold tracking-tight">Payment cancelled</h1>
      <p className="mt-4">You left PayPal without paying. Nothing was charged. Sandbox only.</p>
    </main>
  );
}
