package tr.kunefe.menu;

import java.util.regex.Pattern;

/** Güvenlik: sadece sayısal IPv4 adresli sunuculara girilebilir (alan adı, IPv6 yok). */
public final class IpLock {
    private static final Pattern IPV4 = Pattern.compile(
            "^(?:(?:25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)\\.){3}(?:25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)$");

    private IpLock() {}

    public static boolean allowed(String host) {
        return host != null && IPV4.matcher(host.trim()).matches();
    }

    /** "1.2.3.4:25565" biçiminden sadece adres kısmını alır. */
    public static String hostOf(String address) {
        if (address == null) return "";
        String a = address.trim();
        if (a.startsWith("[")) return a; // IPv6 biçimi: asla izin verilmez
        int i = a.lastIndexOf(':');
        return i > 0 ? a.substring(0, i) : a;
    }
}
