import { createFileRoute } from "@tanstack/react-router";
import { CreateManagerScreen } from "../components/CreateManagerScreen";

const Page = () => (
  <div className="chl-shell" style={{ gridTemplateColumns: "1fr" }}>
    <div className="chl-main">
      <div
        className="chl-content"
        style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
      >
        <CreateManagerScreen />
      </div>
    </div>
  </div>
);

export const Route = createFileRoute("/manager/create")({ component: Page });
