import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import "./index.css";
import Layout from "./components/Layout";
import Destinations from "./pages/Destinations";
import Home from "./pages/Home";
import Planning from "./pages/Planning";
import TripPlan from "./pages/TripPlan";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="planning/:jobId" element={<Planning />} />
            <Route path="trip/:tripId" element={<TripPlan />} />
            <Route path="destinations" element={<Destinations />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
