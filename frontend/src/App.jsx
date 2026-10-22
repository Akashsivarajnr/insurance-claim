import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute, { homeFor } from "./routes/ProtectedRoute";
import PublicLayout from "./layouts/PublicLayout";
import DashboardLayout from "./layouts/DashboardLayout";
import { useAuth } from "./context/AuthContext";
import Landing from "./pages/Landing";
import About from "./pages/About";
import NotFound from "./pages/NotFound";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import CustomerDashboard from "./pages/customer/CustomerDashboard";
import SubmitClaim from "./pages/customer/SubmitClaim";
import MyClaims from "./pages/customer/MyClaims";
import ClaimDetails from "./pages/customer/ClaimDetails";
import Notifications from "./pages/customer/Notifications";
import Profile from "./pages/customer/Profile";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminClaims from "./pages/admin/AdminClaims";
import ClaimReview from "./pages/admin/ClaimReview";
import Settlements from "./pages/admin/Settlements";
import Customers from "./pages/admin/Customers";
import Reports from "./pages/admin/Reports";

function GuestOnly({ children }) {
  const { user } = useAuth();
  return user ? <Navigate to={homeFor(user)} replace /> : children;
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/about" element={<About />} />
        <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
        <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
      </Route>

      <Route element={<ProtectedRoute role="customer" />}>
        <Route path="/customer" element={<DashboardLayout />}>
          <Route index element={<CustomerDashboard />} />
          <Route path="submit" element={<SubmitClaim />} />
          <Route path="claims" element={<MyClaims />} />
          <Route path="claims/:id" element={<ClaimDetails />} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="profile" element={<Profile />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute role="admin" />}>
        <Route path="/admin" element={<DashboardLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="claims" element={<AdminClaims />} />
          <Route path="claims/:id" element={<ClaimReview />} />
          <Route path="settlements" element={<Settlements />} />
          <Route path="customers" element={<Customers />} />
          <Route path="reports" element={<Reports />} />
        </Route>
      </Route>

      <Route path="*" element={<PublicLayout />}><Route path="*" element={<NotFound />} /></Route>
    </Routes>
  );
}
