import { Navigate, Route, Routes } from "react-router-dom";
import { Navbar } from "@/components/Navbar";
import { useAuthStore } from "@/store/authStore";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import ProductsPage from "@/pages/ProductsPage";
import ProductDetailPage from "@/pages/ProductDetailPage";
import CartPage from "@/pages/CartPage";
import CheckoutPage from "@/pages/CheckoutPage";
import OrdersPage from "@/pages/OrdersPage";
import AdminInventoryPage from "@/pages/AdminInventoryPage";
import CreateListingPage from "@/pages/CreateListingPage";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = useAuthStore((s) => s.accessToken);
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function PageContainer({ children }: { children: JSX.Element }) {
  return <div className="max-w-7xl mx-auto px-4 py-6">{children}</div>;
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 w-full bg-slate-50">
        <Routes>
          <Route path="/" element={<ProductsPage />} />
          <Route path="/products/:id" element={<PageContainer><ProductDetailPage /></PageContainer>} />
          <Route path="/login" element={<PageContainer><LoginPage /></PageContainer>} />
          <Route path="/register" element={<PageContainer><RegisterPage /></PageContainer>} />
          <Route
            path="/cart"
            element={
              <RequireAuth>
                <PageContainer><CartPage /></PageContainer>
              </RequireAuth>
            }
          />
          <Route
            path="/checkout"
            element={
              <RequireAuth>
                <PageContainer><CheckoutPage /></PageContainer>
              </RequireAuth>
            }
          />
          <Route
            path="/orders"
            element={
              <RequireAuth>
                <PageContainer><OrdersPage /></PageContainer>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/inventory"
            element={
              <RequireAuth>
                <PageContainer><AdminInventoryPage /></PageContainer>
              </RequireAuth>
            }
          />
          <Route
            path="/sell/new"
            element={
              <RequireAuth>
                <PageContainer><CreateListingPage /></PageContainer>
              </RequireAuth>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
