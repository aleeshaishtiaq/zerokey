import { Auth0Provider, useAuth0 } from '@auth0/auth0-react';
import { useEffect, useState, type ReactNode } from 'react';

const domain = import.meta.env.VITE_AUTH0_DOMAIN?.trim();
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID?.trim();
const audience = import.meta.env.VITE_AUTH0_AUDIENCE?.trim();
const apiBaseUrl = (
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8765'
).trim().replace(/\/+$/, '');

export function AuthGate({ children }: { children: ReactNode }) {
  if (!domain || !clientId || !audience || !apiBaseUrl) {
    return <AccessUnavailable />;
  }

  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        audience,
        redirect_uri: `${window.location.origin}/`,
        scope: 'openid',
      }}
    >
      <AuthenticatedContent>{children}</AuthenticatedContent>
    </Auth0Provider>
  );
}

function AuthenticatedContent({ children }: { children: ReactNode }) {
  const {
    error,
    getAccessTokenSilently,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
    user,
  } = useAuth0();
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [accessError, setAccessError] = useState('');

  useEffect(() => {
    if (!isAuthenticated || !user?.sub) {
      setCheckingAccess(false);
      setIsAuthorized(false);
      return;
    }

    let active = true;
    setCheckingAccess(true);
    setIsAuthorized(false);
    void getAccessTokenSilently()
      .then((accessToken) =>
        fetch(`${apiBaseUrl}/api/auth/check`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        }),
      )
      .then((response) => {
        if (!response.ok) {
          throw new Error(`The staging API denied access (HTTP ${response.status}).`);
        }
        if (active) {
          setIsAuthorized(true);
          setAccessError('');
        }
      })
      .catch((accessError: unknown) => {
        if (active) {
          setIsAuthorized(false);
          setAccessError(
            accessError instanceof Error
              ? accessError.message
              : 'The staging API denied access.',
          );
        }
      })
      .finally(() => {
        if (active) {
          setCheckingAccess(false);
        }
      });
    return () => {
      active = false;
    };
  }, [getAccessTokenSilently, isAuthenticated, user?.sub]);

  if (isLoading) {
    return <AccessUnavailable message="Checking your sign-in…" />;
  }

  if (error) {
    return <AccessUnavailable message={`Sign-in failed: ${error.message}`} />;
  }

  if (!isAuthenticated) {
    return (
      <AccessUnavailable
        action="Sign in"
        onAction={() => void loginWithRedirect()}
        message="Sign in with an identity approved for this staging demo."
      />
    );
  }

  if (!user?.sub) {
    return (
      <AccessUnavailable
        action="Sign out"
        onAction={() => void logout({ logoutParams: { returnTo: `${window.location.origin}/` } })}
        message="Auth0 did not provide an authenticated subject."
      />
    );
  }

  if (checkingAccess) {
    return <AccessUnavailable message="Verifying access with the staging API…" />;
  }
  if (!isAuthorized) {
    return (
      <AccessUnavailable
        action="Sign out"
        onAction={() => void logout({ logoutParams: { returnTo: `${window.location.origin}/` } })}
        message={accessError || 'This identity is not approved for the staging demo.'}
      />
    );
  }

  return <>{children}</>;
}

function AccessUnavailable({
  action,
  message = 'Staging authentication is not configured. Access is denied.',
  onAction,
}: {
  action?: string;
  message?: string;
  onAction?: () => void;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-white">
      <section className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-8">
        <h1 className="text-xl font-semibold">ZeroKey staging access</h1>
        <p role="status" className="mt-3 text-sm text-slate-300">{message}</p>
        {action && onAction && (
          <button
            type="button"
            onClick={onAction}
            className="mt-6 rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold hover:bg-cyan-600"
          >
            {action}
          </button>
        )}
      </section>
    </main>
  );
}
