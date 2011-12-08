Summary: cake - Builds C++ without a makefile
Name: cake
Version: %{version_base}
Release: %{version_release}%{?org_tag}%{?dist}
Source: %{name}-%{version}.tgz
License: GPL3
Group: System/Libraries
Buildroot: %_tmppath/%{name}-%{version}
BuildArch: noarch

%description
cake - a C++ build tool that requires almost no configuration.


%prep
%setup

%build
test %{buildroot} != "/" && rm -rf %{buildroot}

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_sysconfdir}/
mkdir -p %{buildroot}%{_mandir}/man1/

%if %{rhel} > 5
install -m 0644 etc.cake.centos6 %{buildroot}%{_sysconfdir}/cake.conf
%else
install -m 0644 etc.cake.centos5 %{buildroot}%{_sysconfdir}/cake.conf
%endif
install cake %{buildroot}%{_bindir}
install -m 0644 cake.1 %{buildroot}%{_mandir}/man1/

%clean
test "%{buildroot}" != "/" && rm -rf %{buildroot}

%files
%defattr(-,root,root)
%attr(0755,-,-)%{_bindir}/cake
%config(noreplace)%attr(0644,-,-)%{_sysconfdir}/cake.conf
%attr(0644,-,-)%{_mandir}/man1/cake.1.gz



