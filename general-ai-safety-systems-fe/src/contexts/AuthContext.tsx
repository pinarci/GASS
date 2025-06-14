import { createContext, useContext, useState, ReactNode } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  userType: 'admin' | 'customer' | null;
  login: (email: string, password: string, userType: 'admin' | 'customer') => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userType, setUserType] = useState<'admin' | 'customer' | null>(null);

  const login = async (email: string, password: string, userType: 'admin' | 'customer') => {
    // TODO: Implement actual authentication logic with backend
    // For now, we'll just simulate a successful login
    setIsAuthenticated(true);
    setUserType(userType);
  };

  const logout = () => {
    setIsAuthenticated(false);
    setUserType(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, userType, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
} 