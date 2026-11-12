import { PageTitle } from "@/components/ui";
import { AdminGate } from "@/components/admin/use-admin";
import { ConnectView } from "@/components/admin/connect-view";

export const metadata = { title: "Connect · ShelfReady" };

export default function Page() {
  return (
    <div>
      <PageTitle icon="connect">Connect</PageTitle>
      <p className="mt-3 mb-6 max-w-2xl">
        Check the backend and the PayPal sandbox connection, and preview your PayPal catalog.
      </p>
      <AdminGate>
        <ConnectView />
      </AdminGate>
    </div>
  );
}
