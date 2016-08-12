%global owner Zomojo
%global srcname compiletools
%global sum C++ build tools that requires almost no configuration.
%global version_base 4.0.4
%global version_release 1

Summary: %sum
Name: python-%{srcname}
Version: %{version_base}
Release: %{version_release}%{?org_tag}%{?dist}
Source: %{name}-%{version}.tgz
Source0: https://github.com/%{owner}/%{srcname}/archive/%{srcname}-%{version_base}-%{version_release}.tar.gz
License: GPL3
Group: System/Libraries
Buildroot: %_tmppath/%{name}-%{version}
BuildArch: noarch
BuildRequires: python-setuptools python-docutils python2-devel python3-devel
Obsoletes: cake

%description
%sum

%package -n python2-%{srcname}
Requires: python2-configargparse python-appdirs 
Summary:        %{sum}
%{?python_provide:%python_provide python2-%{srcname}}

%description -n python2-%{srcname}
%sum

#%package -n python3-%{srcname}
#Requires: python3-configargparse python3-appdirs 
#Summary:        %{sum}
#%{?python_provide:%python_provide python3-%{srcname}}

#%description -n python3-%{srcname}
#%sum

%prep
%autosetup -n %{srcname}-%{version}

%build
./create-documentation
%py2_build
%py3_build

%files
%defattr(-,root,root)
%attr(0755,-,-)%{_bindir}/ct-*
%config(noreplace)%attr(0644,-,-)%{_sysconfdir}/ct
%attr(0644,-,-)%{_mandir}/man1/*.1.gz


%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_sysconfdir}/xdg/ct/
mkdir -p %{buildroot}%{_mandir}/man1/

install -m 0644 -t %{buildroot}%{_sysconfdir}/ct/ ct.conf.d/*
install -m 0644 -t %{buildroot}%{_mandir}/man1/ *.1

# Note that the py2 setup.py will overwrite the py3 in /usr/bin
#%py3_install
#%py2_install
# --root $RPM_BUILD_ROOT makes the package install with a single, expanded
# directory in %{python2_sitelib} and a separate egginfo directory.
%{__python2} setup.py install --skip-build --root $RPM_BUILD_ROOT 

%check
#%{__python3} setup.py test
%{__python2} setup.py test

# Note that there is no %%files section for the unversioned python module if we are building for several python runtimes
%files -n python2-%{srcname}
%license LICENCE.txt
%doc README.rst
%{python2_sitelib}/*
%{_bindir}/ct-*
%{_mandir}/man1/*.1.gz

#%files -n python3-%{srcname}
#%license LICENCE.txt
#%doc README.rst
#%{python3_sitelib}/*
#%{_bindir}/ct-*
#%{_mandir}/man1/*.1.gz

%changelog
