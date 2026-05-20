() => {
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
    });

    Object.defineProperty(navigator, 'languages', {
        get: () => ['ru-RU', 'ru', 'en-US', 'en'],
    });

    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });

    Object.defineProperty(navigator, 'permissions', {
        get: () => ({
            query: () => Promise.resolve({ state: 'granted' }),
        }),
    });

    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);

    window.chrome = {
        runtime: {},
        app: {
            isInstalled: false,
        },
        webstore: {
            installState: 'installed',
            onInstallStageChanged: {},
            onDownloadProgress: {},
        },
        csi: () => {},
        loadTimes: () => {},
        getVariableValue: () => {},
        getResourceBundle: () => {},
        canary: false,
        loadTimes: () => {},
        csi: () => {},
    ;

    Object.defineProperty(navigator, 'chrome', {
        get: () => window.chrome,
    });

    Object.defineProperty(HTMLNavigator.prototype, 'userAgent', {
        get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    });
