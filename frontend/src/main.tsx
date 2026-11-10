import "@fontsource-variable/inter";
import "./styles/index.css";
import "./i18n";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router";

import { Providers } from "./app/Providers";
import { routes } from "./app/routes";
import { applyTheme, readTheme, watchSystemTheme } from "./lib/theme";

applyTheme(readTheme());
watchSystemTheme(readTheme);

const router = createBrowserRouter(routes);
const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element");

createRoot(root).render(
  <StrictMode>
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  </StrictMode>,
);
