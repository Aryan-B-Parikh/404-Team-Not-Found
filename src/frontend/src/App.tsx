import { Providers } from "./app/providers";
import MainApp from "./app/App";

export default function App() {
  return (
    <Providers>
      <MainApp />
    </Providers>
  );
}
