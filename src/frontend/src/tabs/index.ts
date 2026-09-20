// Tab registry. Each tab lives in its own file so four people never touch the same file.
import Bob from "./Bob";
import BerthCranes from "./BerthCranes";
import Forecast from "./Forecast";
import Overview from "./Overview";
import Plan from "./Plan";
import Routing from "./Routing";

export const TABS = [
  { id: "overview", label: "Overview", Component: Overview },
  { id: "forecast", label: "Forecast", Component: Forecast },
  { id: "berth", label: "Berth & Cranes", Component: BerthCranes },
  { id: "routing", label: "Routing", Component: Routing },
  { id: "plan", label: "72-Hr Plan", Component: Plan },
  { id: "bob", label: "Bob AI", Component: Bob },
] as const;

export type TabId = (typeof TABS)[number]["id"];
