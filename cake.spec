
Summary: cake - Builds C++ without a makefile
Name: cake
Version: %{version_base}
Release: %{version_release}%{org_tag}%{dist}
Source: %{name}-%{version}.tgz
License: Copyright Zomojo Pty. Ltd.
Group: System/Libraries
Buildroot: %_tmppath/%{name}-%{version}
Prefix: /usr
BuildArch: noarch

%description
cake builds C++ fast and accurately, without
any configuration files.


%prep
%setup

%build
test %{buildroot} != "/" && rm -rf %{buildroot}

%install
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/etc/

%if %{rhel} > 5
cp etc.cake.centos6 %{buildroot}/etc/cake.conf
%else
cp etc.cake.centos5 %{buildroot}/etc/cake.conf
%endif
cp cake %{buildroot}/usr/bin
cp cake-* %{buildroot}/usr/bin
chmod -R 755 %{buildroot}/usr/bin

%clean
test "%{buildroot}" != "/" && rm -rf %{buildroot}

%files
%defattr(-,root,root)
%attr(0755,-,-)/usr/bin/cake
%attr(0755,-,-)/usr/bin/cake-*
/etc/cake.conf


