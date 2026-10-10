import { Route, Routes } from "react-router";

import { SiteFooter } from "./components/SiteFooter";
import { SiteNav } from "./components/SiteNav";
import { Home } from "./pages/Home";
import { WorldDetail } from "./pages/WorldDetail";

export function App() {
  return (
    <>
      <SiteNav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/worlds/:id" element={<WorldDetail />} />
      </Routes>
      <SiteFooter />
    </>
  );
}
