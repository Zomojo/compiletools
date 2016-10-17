%global owner Zomojo
%global srcname compiletools
%global sum C++ build tools that requires almost no configuration.
%global version_base 4.1.31
%global version_release 1

Summary: %sum
Name: python-%{srcname}
Version: %{version_base}
Release: %{version_release}%{?org_tag}%{?dist}
Source0: https://github.com/%{owner}/%{srcname}/archive/v%{version_base}.tar.gz
License: GPLv3+
Group: Development/Libraries
Buildroot: %_tmppath/%{name}-%{version}
BuildArch: noarch
Url: http://zomojo.github.io/compiletools/
BuildRequires: python-setuptools python-docutils python2-configargparse python-appdirs python2-devel 
Obsoletes: cake
Provides: cake
Requires: python-setuptools python2-configargparse python-appdirs python-%{srcname}

%description
%sum

%prep
%autosetup -p0 -n %{srcname}-%{version}

%build
./create-documentation
python setup.py build

%check
python setup.py test

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_sysconfdir}/xdg/ct/
mkdir -p %{buildroot}%{_mandir}/man1/
mkdir -p %{buildroot}%{_datadir}/licenses/python-%{srcname}/

install -m 0644 -t %{buildroot}%{_mandir}/man1/ *.1

# --root $RPM_BUILD_ROOT makes the package install with a single, expanded
# directory in %{python2_sitelib} and a separate egginfo directory.
python setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

# Make cake point to ct-cake
pushd %{buildroot}%{_bindir}/
ln -s ct-cake cake
popd

%clean
rm -rf %{buildroot}

%files
%{!?_licensedir:%global license %%doc}
%license LICENSE.txt
%doc README.rst
%{_mandir}/man1/*.1.gz
%{_sysconfdir}/xdg/ct
%{python_sitelib}/*
%{_bindir}/ct-*
%{_bindir}/cake

%changelog
