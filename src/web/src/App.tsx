import { Route, Routes } from "react-router";

import { TopBar } from "./components/TopBar";
import { Home } from "./pages/Home";
import { WorldDetail } from "./pages/WorldDetail";

export function App() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/worlds/:id" element={<WorldDetail />} />
      </Routes>
    </>
  );
}
