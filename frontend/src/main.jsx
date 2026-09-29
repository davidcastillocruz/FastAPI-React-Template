import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { ThemeProvider } from "@/features/shared/theme/ThemeProvider";
import Homepage from "@/pages/homepage/Homepage";
import NotFound from "@/pages/notfound/NotFound";

import "@/features/shared/styles/themes.css";
import "@/features/shared/styles/animations.css";
import "@/index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <Routes>
          <Route path="/" element={<Homepage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
);